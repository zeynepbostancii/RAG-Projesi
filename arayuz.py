"""
Streamlit arayuzu — artik veritabanina dogrudan dokunmuyor.

Her islem API uzerinden yapiliyor. Bu sayede:
- Veritabani kilidi sorunu yok (sahibi tek: API)
- Arayuz degistirilebilir, mantik ayni kalir
- Baska istemciler de ayni API'yi kullanabilir

Calistirma sirasi:
    1. uvicorn api:app --port 8000
    2. streamlit run arayuz.py
"""

import requests
import streamlit as st

import sohbetler

API = "http://localhost:8000"

st.set_page_config(page_title="Dokuman Asistani", layout="wide")


def api_get(yol, **kw):
    return requests.get(f"{API}{yol}", timeout=30, **kw)


def api_post(yol, **kw):
    return requests.post(f"{API}{yol}", timeout=300, **kw)


# --- Servis ayakta mi ---
try:
    api_get("/saglik")
except requests.exceptions.RequestException:
    st.error(
        "API'ye baglanilamadi. Once baska bir terminalde su komutu calistir:\n\n"
        "`uvicorn api:app --port 8000`"
    )
    st.stop()


if "son_yuklenenler" not in st.session_state:
    st.session_state.son_yuklenenler = None

if "aktif" not in st.session_state:
    liste = sohbetler.hepsini_getir()
    st.session_state.aktif = next(iter(liste)) if liste else sohbetler.yeni()


# ---------------- Kenar cubugu ----------------

with st.sidebar:
    st.header("Sohbetler")

    if st.button("Yeni sohbet", type="primary", use_container_width=True):
        st.session_state.aktif = sohbetler.yeni()
        st.rerun()

    for kimlik, bilgi in sohbetler.hepsini_getir().items():
        s1, s2 = st.columns([5, 1])
        etiket = ("▸ " if kimlik == st.session_state.aktif else "") + bilgi["ad"]
        if s1.button(etiket, key=f"ac_{kimlik}", use_container_width=True):
            st.session_state.aktif = kimlik
            st.rerun()
        if s2.button("×", key=f"sils_{kimlik}"):
            sohbetler.sil(kimlik)
            kalan = sohbetler.hepsini_getir()
            if st.session_state.aktif == kimlik:
                st.session_state.aktif = (
                    next(iter(kalan)) if kalan else sohbetler.yeni()
                )
            st.rerun()

    st.divider()
    st.header("Dosya yukle")

    dosyalar = st.file_uploader(
        "Dosya sec",
        type=["pdf", "docx", "xlsx", "pptx", "txt", "md"],
        accept_multiple_files=True,
    )
    yontem = st.radio(
        "Parcalama", ["semantik", "sabit"], horizontal=True,
    )

    if st.button("Isle") and dosyalar:
        basarili = []
        for d in dosyalar:
            with st.spinner(f"{d.name} isleniyor..."):
                try:
                    cevap = api_post(
                        "/dokumanlar",
                        files={"dosya": (d.name, d.getvalue())},
                        params={"yontem": yontem},
                    )
                except requests.exceptions.RequestException as hata:
                    st.error(f"{d.name}: baglanti hatasi ({hata})")
                    continue

            if cevap.status_code == 200:
                adet = cevap.json()["parca_sayisi"]
                st.success(f"{d.name}: {adet} parca")
                basarili.append(d.name)
            else:
                st.error(f"{d.name}: {cevap.json().get('detail', 'hata')}")

        st.session_state.son_yuklenenler = basarili
        st.rerun()

    st.divider()
    st.header("Arama kapsami")

    bilgi = api_get("/dokumanlar").json()
    mevcut = {d["ad"]: d["parca_sayisi"] for d in bilgi["dosyalar"]}

    if not mevcut:
        st.info("Henuz dokuman yok.")
        secili = []
    else:
        son = st.session_state.son_yuklenenler
        varsayilan = [d for d in (son or []) if d in mevcut] or list(mevcut)

        secili = st.multiselect(
            "Bu dosyalarda ara", options=list(mevcut), default=varsayilan
        )

        if st.button("Tumunu sec"):
            st.session_state.son_yuklenenler = None
            st.rerun()

        st.caption(f"Toplam {bilgi['toplam_parca']} parca")

        with st.expander("Dosya yonetimi"):
            for ad, adet in mevcut.items():
                k1, k2 = st.columns([3, 1])
                k1.caption(f"{ad} ({adet})")
                if k2.button("Sil", key=f"sild_{ad}"):
                    requests.delete(f"{API}/dokumanlar/{ad}", timeout=30)
                    st.rerun()

    st.divider()
    st.caption(f"API: {API}")


# ---------------- Ana ekran ----------------

aktif = sohbetler.getir(st.session_state.aktif)
if aktif is None:
    st.session_state.aktif = sohbetler.yeni()
    aktif = sohbetler.getir(st.session_state.aktif)

turlar = aktif["turlar"]

st.title("Dokuman Asistani")
st.caption(aktif["ad"])

for tur in turlar:
    with st.chat_message("user"):
        st.write(tur["soru"])
    with st.chat_message("assistant"):
        st.write(tur["cevap"])
        if tur.get("yazilan"):
            st.caption(f"Arama sorusu: {tur['yazilan']}")
        if tur.get("kaynaklar"):
            st.caption("Kaynak: " + ", ".join(tur["kaynaklar"]))
        if tur.get("parcalar"):
            with st.expander("Kullanilan parcalar"):
                for i, p in enumerate(tur["parcalar"]):
                    ek = (f" / reranker {p['reranker_skor']:.3f}"
                          if p.get("reranker_skor") is not None else "")
                    st.caption(
                        f"[{i+1}] {p['dosya']} / parca {p['parca_no']} "
                        f"/ vektor {p['vektor_skor']:.3f}{ek}"
                    )
                    st.text(p["metin"][:400])


soru = st.chat_input("Sorunuz")

if soru:
    if not secili:
        st.warning("Arama yapilacak dosya secili degil.")
    else:
        with st.chat_message("user"):
            st.write(soru)

        with st.chat_message("assistant"):
            with st.spinner("Cevap uretiliyor..."):
                govde = {
                    "soru": soru,
                    "dosyalar": secili if len(secili) < len(mevcut) else None,
                    "gecmis": [
                        {"soru": t["soru"], "cevap": t["cevap"]}
                        for t in turlar
                    ],
                }
                try:
                    cevap = api_post("/sor", json=govde)
                except requests.exceptions.RequestException as hata:
                    st.error(f"API hatasi: {hata}")
                    st.stop()

            if cevap.status_code != 200:
                try:
                    mesaj = cevap.json().get("detail", "Bilinmeyen hata")
                except Exception:
                    mesaj = f"API hatasi {cevap.status_code}: {cevap.text[:500]}"
                st.error(mesaj)
                st.stop()

            veri = cevap.json()
            st.write(veri["cevap"])

            if veri.get("arama_sorusu"):
                st.caption(f"Arama sorusu: {veri['arama_sorusu']}")
            if veri.get("kaynaklar"):
                st.caption("Kaynak: " + ", ".join(veri["kaynaklar"]))

            sohbetler.tur_ekle(st.session_state.aktif, {
                "soru": soru,
                "cevap": veri["cevap"],
                "kaynaklar": veri.get("kaynaklar", []),
                "yazilan": veri.get("arama_sorusu"),
                "parcalar": veri.get("parcalar", []),
            })

        st.rerun()