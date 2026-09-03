import uuid
from pathlib import Path

import streamlit as st
import ollama
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, MatchAny,
)

from okuyucular import OKUYUCULAR
from parcalayici import sabit_parcala, semantik_parcala
import sohbetler

st.set_page_config(page_title="Dokuman Asistani", layout="wide")

KOLEKSIYON = "dokumanlar"
BOYUT = 384
MODEL_ADI = "qwen2.5:7b"

EMBEDDING_ADI = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_ADI = "BAAI/bge-reranker-base"

ADAY_SAYISI = 20
SONUC_SAYISI = 5
RERANK_ESIK = None  # esik yok: sabit sayida en iyi sonuc alinir
GECMIS_TUR = 3

YENIDEN_YAZ = """Kullanicinin son sorusunu arama motoruna verilecek tek bir
soru haline getir.

Son soruda eksik olan konuyu sohbet gecmisinden al ve soruya ekle.
Son soru zaten tek basina anlasiliyorsa aynen tekrarla.

ORNEKLER
Gecmis: "RISK-014 nedir" sorulmus.
Son soru: kim sorumlu
Cikti: RISK-014 riskinden kim sorumlu

Gecmis: "Deniz Alparslan kimdir" sorulmus.
Son soru: gunluk ucreti ne kadar
Cikti: Deniz Alparslan gunluk ucreti

Gecmis: "butce ne kadar" sorulmus.
Son soru: go-live tarihi ne zaman
Cikti: go-live tarihi ne zaman

Gecmis: "Ceyda Nurlu kimdir" sorulmus.
Son soru: nerede calisiyor
Cikti: Ceyda Nurlu calisma lokasyonu

KURALLAR
- Sadece soruyu yaz. Aciklama, yorum, gerekce yazma.
- En fazla 12 kelime.
- Bilgi bulunmadigini soyleme, sadece soruyu yeniden yaz.

Gecmis:
{gecmis}

Son soru: {soru}
Cikti:"""

SABLON = """Asagidaki metin parcalarini oku ve soruyu cevapla.

Kurallar:
- Cevabini SADECE asagidaki parcalara dayandir.
- Parcalarda konuyla ilgili hicbir sey yoksa "Bu bilgi dokumanlarda bulunmuyor." yaz.
- Sayilari, tarihleri ve isimleri parcada yazdigi gibi aktar. Hesaplama yapma,
  yuzdeye cevirme, farkli parcalardaki bilgileri birbirine karistirma.
- Soru bir kisi veya kod hakkindaysa, sadece o kisiye/koda ait satirlari kullan.
- Ayni konuda birden fazla deger varsa (ornegin revize edilmis bir tarih)
  ikisini de belirt.
- En fazla 3 cumle yaz.
- Kullanicinin dilinde cevapla.

--- PARCALAR ---
{baglam}
--- PARCALAR SONU ---

SORU: {soru}

CEVAP:"""


@st.cache_resource
def yukle():
    model = SentenceTransformer(EMBEDDING_ADI)

    try:
        reranker = CrossEncoder(RERANKER_ADI)
    except Exception as hata:
        reranker = None
        print(f"Reranker yuklenemedi, rerankersiz devam: {hata}")

    client = QdrantClient(path="./vektor_db")
    if not client.collection_exists(KOLEKSIYON):
        client.create_collection(
            collection_name=KOLEKSIYON,
            vectors_config=VectorParams(size=BOYUT, distance=Distance.COSINE),
        )
    return model, reranker, client


model, reranker, client = yukle()

if "son_yuklenenler" not in st.session_state:
    st.session_state.son_yuklenenler = None

# Aktif sohbet: yoksa en son sohbeti ac, o da yoksa yeni olustur
if "aktif" not in st.session_state:
    mevcut_sohbetler = sohbetler.hepsini_getir()
    if mevcut_sohbetler:
        st.session_state.aktif = next(iter(mevcut_sohbetler))
    else:
        st.session_state.aktif = sohbetler.yeni()


def yuklu_dosyalar():
    sayac = {}
    sonraki = None
    while True:
        kayitlar, sonraki = client.scroll(
            collection_name=KOLEKSIYON,
            limit=1000,
            offset=sonraki,
            with_payload=["dosya"],
            with_vectors=False,
        )
        for k in kayitlar:
            ad = k.payload.get("dosya", "?")
            sayac[ad] = sayac.get(ad, 0) + 1
        if sonraki is None:
            break
    return dict(sorted(sayac.items()))


def dosya_sil(ad):
    client.delete(
        collection_name=KOLEKSIYON,
        points_selector=Filter(must=[
            FieldCondition(key="dosya", match=MatchValue(value=ad))
        ]),
    )


def dosyayi_isle(dosya, yontem="semantik"):
    uzanti = Path(dosya.name).suffix.lower()
    okuyucu = OKUYUCULAR.get(uzanti)

    if okuyucu is None:
        return -1

    metin = okuyucu(dosya)

    if len(metin.strip()) == 0:
        return 0

    dosya_sil(dosya.name)

    if yontem == "semantik":
        parcalar = semantik_parcala(metin, model)
    else:
        parcalar = sabit_parcala(metin)

    if not parcalar:
        return 0

    vektorler = model.encode(parcalar)
    noktalar = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{dosya.name}-{i}")),
            vector=vektorler[i].tolist(),
            payload={"dosya": dosya.name, "parca_no": i, "metin": p,
                     "yontem": yontem},
        )
        for i, p in enumerate(parcalar)
    ]
    client.upsert(collection_name=KOLEKSIYON, points=noktalar)
    return len(noktalar)


def soruyu_yeniden_yaz(soru, turlar):
    if not turlar:
        return soru, False

    son_turlar = turlar[-GECMIS_TUR:]
    gecmis = "\n".join(
        f"Kullanici: {t['soru']}\nAsistan: {t['cevap'][:300]}"
        for t in son_turlar
    )

    try:
        yanit = ollama.chat(
            model=MODEL_ADI,
            messages=[{"role": "user",
                       "content": YENIDEN_YAZ.format(gecmis=gecmis, soru=soru)}],
            options={"temperature": 0.0},
        )
        yeni = yanit["message"]["content"].strip().strip('"').split("\n")[0]
    except Exception:
        return soru, False

    # Model soru yerine aciklama yazarsa orijinali kullan
    supheli = [
        "ancak", "bulunmamakta", "soruyorsunuz", "bu durumda",
        "yeniden sekillendir", "bilgi verilebilir", "sohbet gecmisi",
        "sohbet geçmişi", "aciklama", "açıklama",
    ]
    kelime_sayisi = len(yeni.split())

    if (not yeni
            or kelime_sayisi > 20
            or len(yeni) > 160
            or any(k in yeni.lower() for k in supheli)):
        return soru, False

    return yeni, yeni.lower() != soru.lower()


# ---------------- Kenar cubugu ----------------

with st.sidebar:
    st.header("Sohbetler")

    if st.button("Yeni sohbet", type="primary", use_container_width=True):
        st.session_state.aktif = sohbetler.yeni()
        st.rerun()

    liste = sohbetler.hepsini_getir()

    for kimlik, bilgi in liste.items():
        sut1, sut2 = st.columns([5, 1])
        etiket = bilgi["ad"]
        if kimlik == st.session_state.aktif:
            etiket = "▸ " + etiket

        if sut1.button(etiket, key=f"ac_{kimlik}", use_container_width=True):
            st.session_state.aktif = kimlik
            st.rerun()

        if sut2.button("×", key=f"sil_s_{kimlik}", help="Sohbeti sil"):
            sohbetler.sil(kimlik)
            if st.session_state.aktif == kimlik:
                kalan = sohbetler.hepsini_getir()
                st.session_state.aktif = (
                    next(iter(kalan)) if kalan else sohbetler.yeni()
                )
            st.rerun()

    st.divider()
    st.header("Dosya yukle")

    desteklenen = [u.lstrip(".") for u in OKUYUCULAR.keys()]
    dosyalar = st.file_uploader(
        "Dosya sec",
        type=desteklenen,
        accept_multiple_files=True,
    )

    yontem = st.radio(
        "Parcalama yontemi",
        options=["semantik", "sabit"],
        format_func=lambda x: "Semantik" if x == "semantik" else "Sabit (800)",
        horizontal=True,
    )

    temizle = st.checkbox("Once mevcut dokumanlari sil", value=False)

    if st.button("Isle") and dosyalar:
        if temizle:
            for eski in yuklu_dosyalar():
                dosya_sil(eski)

        basarili = []
        for d in dosyalar:
            with st.spinner(f"{d.name} isleniyor..."):
                adet = dosyayi_isle(d, yontem)
            if adet == -1:
                st.error(f"{d.name}: desteklenmeyen tip")
            elif adet == 0:
                st.error(f"{d.name}: metin cikarilamadi")
            else:
                st.success(f"{d.name}: {adet} parca")
                basarili.append(d.name)

        st.session_state.son_yuklenenler = basarili
        st.rerun()

    st.divider()
    st.header("Arama kapsami")
    mevcut = yuklu_dosyalar()

    if not mevcut:
        st.info("Henuz dokuman yok.")
        secili = []
    else:
        son = st.session_state.son_yuklenenler
        varsayilan = [d for d in (son or []) if d in mevcut] or list(mevcut.keys())

        secili = st.multiselect(
            "Bu dosyalarda ara",
            options=list(mevcut.keys()),
            default=varsayilan,
        )

        if st.button("Tumunu sec"):
            st.session_state.son_yuklenenler = None
            st.rerun()

        st.caption(f"Toplam {sum(mevcut.values())} parca")

        with st.expander("Dosya yonetimi"):
            for ad, adet in mevcut.items():
                s1, s2 = st.columns([3, 1])
                s1.caption(f"{ad} ({adet})")
                if s2.button("Sil", key=f"sil_d_{ad}"):
                    dosya_sil(ad)
                    st.rerun()

    st.divider()
    st.caption("Reranker: " + ("aktif" if reranker else "kapali"))
    st.caption("Model: " + MODEL_ADI)


# ---------------- Ana ekran ----------------

aktif_sohbet = sohbetler.getir(st.session_state.aktif)
if aktif_sohbet is None:
    st.session_state.aktif = sohbetler.yeni()
    aktif_sohbet = sohbetler.getir(st.session_state.aktif)

turlar = aktif_sohbet["turlar"]

st.title("Dokuman Asistani")
st.caption(aktif_sohbet["ad"])

for tur in turlar:
    with st.chat_message("user"):
        st.write(tur["soru"])
    with st.chat_message("assistant"):
        st.write(tur["cevap"])
        if tur.get("yazilan"):
            st.caption(f"Arama sorusu: {tur['yazilan']}")
        if tur.get("kaynaklar"):
            st.caption("Kaynak: " + ", ".join(tur["kaynaklar"]))


soru = st.chat_input("Sorunuz")

if soru:
    if not secili:
        st.warning("Arama yapilacak dosya secili degil.")
    else:
        with st.chat_message("user"):
            st.write(soru)

        with st.chat_message("assistant"):
            with st.spinner("Araniyor..."):
                arama_sorusu, degisti = soruyu_yeniden_yaz(soru, turlar)

                if len(secili) < len(mevcut):
                    arama_filtresi = Filter(must=[
                        FieldCondition(key="dosya", match=MatchAny(any=secili))
                    ])
                else:
                    arama_filtresi = None

                adaylar = client.query_points(
                    collection_name=KOLEKSIYON,
                    query=model.encode(arama_sorusu).tolist(),
                    query_filter=arama_filtresi,
                    limit=ADAY_SAYISI if reranker else SONUC_SAYISI,
                ).points

                if adaylar and reranker:
                    ciftler = [(arama_sorusu, a.payload["metin"]) for a in adaylar]
                    skorlar = reranker.predict(ciftler)
                    sirali = sorted(zip(adaylar, skorlar),
                                    key=lambda x: x[1], reverse=True)
                    if RERANK_ESIK is not None:
                        elenmis = [(a, s) for a, s in sirali if s >= RERANK_ESIK]
                        sirali = elenmis or sirali[:1]
                    sonuclar = sirali[:SONUC_SAYISI]
                else:
                    sonuclar = [(a, None) for a in adaylar[:SONUC_SAYISI]]

            if not sonuclar:
                metin = "Secili dosyalarda sonuc bulunamadi."
                st.warning(metin)
                sohbetler.tur_ekle(st.session_state.aktif, {
                    "soru": soru, "cevap": metin,
                    "kaynaklar": [], "yazilan": None,
                })
            else:
                baglam = "".join(
                    f"\n[Parca {i+1} | kaynak: {a.payload['dosya']}]\n"
                    f"{a.payload['metin']}\n"
                    for i, (a, s) in enumerate(sonuclar)
                )

                with st.spinner("Cevap uretiliyor..."):
                    yanit = ollama.chat(
                        model=MODEL_ADI,
                        messages=[{"role": "user",
                                   "content": SABLON.format(
                                       baglam=baglam, soru=arama_sorusu)}],
                        options={"temperature": 0.1},
                    )
                metin = yanit["message"]["content"]

                st.write(metin)

                kaynaklar = sorted({a.payload["dosya"] for a, s in sonuclar})
                if degisti:
                    st.caption(f"Arama sorusu: {arama_sorusu}")
                st.caption("Kaynak: " + ", ".join(kaynaklar))

                with st.expander("Kullanilan parcalar"):
                    for i, (a, s) in enumerate(sonuclar):
                        ek = f" / reranker {s:.3f}" if s is not None else ""
                        st.caption(
                            f"[{i+1}] {a.payload['dosya']} / "
                            f"parca {a.payload['parca_no']} / "
                            f"vektor {a.score:.3f}{ek}"
                        )
                        st.text(a.payload["metin"][:400])

                sohbetler.tur_ekle(st.session_state.aktif, {
                    "soru": soru,
                    "cevap": metin,
                    "kaynaklar": kaynaklar,
                    "yazilan": arama_sorusu if degisti else None,
                })

        st.rerun()