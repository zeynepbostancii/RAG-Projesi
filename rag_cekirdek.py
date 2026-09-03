"""
RAG cekirdegi: arayuzden bagimsiz tum mantik burada.

Streamlit, FastAPI veya baska bir arayuz bu modulu kullanabilir.
Bu ayrim onemli: is mantigi tek yerde durur, arayuz degistiginde
yeniden yazilmaz.
"""

import uuid
from pathlib import Path

import ollama
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, MatchAny,
)

from okuyucular import OKUYUCULAR
from parcalayici import sabit_parcala, semantik_parcala

KOLEKSIYON = "dokumanlar"
BOYUT = 384
MODEL_ADI = "qwen2.5:7b"

EMBEDDING_ADI = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_ADI = "BAAI/bge-reranker-base"

ADAY_SAYISI = 20
SONUC_SAYISI = 5
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
  farkli parcalardaki bilgileri birbirine karistirma.
- Soru bir kisi veya kod hakkindaysa, sadece o kisiye/koda ait satirlari kullan.
- Ayni konuda birden fazla deger varsa ikisini de belirt.
- En fazla 3 cumle yaz.
- Kullanicinin dilinde cevapla.

--- PARCALAR ---
{baglam}
--- PARCALAR SONU ---

SORU: {soru}

CEVAP:"""

_model = None
_reranker = None
_client = None


def baslat():
    """Modelleri ve veritabanini bir kez yukler."""
    global _model, _reranker, _client

    if _client is not None:
        return

    _model = SentenceTransformer(EMBEDDING_ADI)

    try:
        _reranker = CrossEncoder(RERANKER_ADI)
    except Exception as hata:
        _reranker = None
        print(f"Reranker yuklenemedi: {hata}")

    _client = QdrantClient(path="./vektor_db")
    if not _client.collection_exists(KOLEKSIYON):
        _client.create_collection(
            collection_name=KOLEKSIYON,
            vectors_config=VectorParams(size=BOYUT, distance=Distance.COSINE),
        )


def kapat():
    global _client
    if _client is not None:
        _client.close()
        _client = None


def dosyalari_listele():
    """Veritabanindaki dosyalari ve parca sayilarini dondurur."""
    sayac = {}
    sonraki = None
    while True:
        kayitlar, sonraki = _client.scroll(
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
    _client.delete(
        collection_name=KOLEKSIYON,
        points_selector=Filter(must=[
            FieldCondition(key="dosya", match=MatchValue(value=ad))
        ]),
    )


def dokuman_ekle(dosya_adi, ikili_veri, yontem="semantik"):
    """
    Dosyayi okur, parcalar, vektore cevirir ve kaydeder.

    ikili_veri: dosyanin ham baytlari (BytesIO ya da bytes)
    Donen deger: eklenen parca sayisi. -1 = desteklenmeyen tip, 0 = metin yok
    """
    import io

    uzanti = Path(dosya_adi).suffix.lower()
    okuyucu = OKUYUCULAR.get(uzanti)
    if okuyucu is None:
        return -1

    akis = io.BytesIO(ikili_veri) if isinstance(ikili_veri, bytes) else ikili_veri
    metin = okuyucu(akis)

    if not metin or not metin.strip():
        return 0

    dosya_sil(dosya_adi)

    if yontem == "semantik":
        parcalar = semantik_parcala(metin, _model)
    else:
        parcalar = sabit_parcala(metin)

    if not parcalar:
        return 0

    vektorler = _model.encode(parcalar)
    noktalar = [
        PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{dosya_adi}-{i}")),
            vector=vektorler[i].tolist(),
            payload={"dosya": dosya_adi, "parca_no": i,
                     "metin": p, "yontem": yontem},
        )
        for i, p in enumerate(parcalar)
    ]
    _client.upsert(collection_name=KOLEKSIYON, points=noktalar)
    return len(noktalar)


def soruyu_yeniden_yaz(soru, gecmis_turlar):
    if not gecmis_turlar:
        return soru, False

    son = gecmis_turlar[-GECMIS_TUR:]
    gecmis = "\n".join(
        f"Kullanici: {t['soru']}\nAsistan: {t.get('cevap','')[:300]}"
        for t in son
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

    supheli = ["ancak", "bulunmamakta", "soruyorsunuz", "bu durumda",
               "yeniden sekillendir", "bilgi verilebilir", "sohbet"]

    if (not yeni or len(yeni.split()) > 20 or len(yeni) > 160
            or any(k in yeni.lower() for k in supheli)):
        return soru, False

    return yeni, yeni.lower() != soru.lower()


def ara(soru, dosyalar=None, adet=SONUC_SAYISI):
    """Soruya en uygun parcalari dondurur. LLM cagrisi yapmaz."""
    if dosyalar:
        filtre = Filter(must=[
            FieldCondition(key="dosya", match=MatchAny(any=list(dosyalar)))
        ])
    else:
        filtre = None

    adaylar = _client.query_points(
        collection_name=KOLEKSIYON,
        query=_model.encode(soru).tolist(),
        query_filter=filtre,
        limit=ADAY_SAYISI if _reranker else adet,
    ).points

    if not adaylar:
        return []

    if _reranker:
        ciftler = [(soru, a.payload["metin"]) for a in adaylar]
        skorlar = _reranker.predict(ciftler)
        sirali = sorted(zip(adaylar, skorlar), key=lambda x: x[1], reverse=True)
        secilen = sirali[:adet]
    else:
        secilen = [(a, None) for a in adaylar[:adet]]

    return [
        {
            "dosya": a.payload["dosya"],
            "parca_no": a.payload["parca_no"],
            "metin": a.payload["metin"],
            "vektor_skor": float(a.score),
            "reranker_skor": float(s) if s is not None else None,
        }
        for a, s in secilen
    ]


def cevapla(soru, dosyalar=None, gecmis=None):
    """
    Tam RAG akisi: soruyu yeniden yaz, ara, LLM'e sor.

    Donen deger: cevap metni, kullanilan parcalar, arama sorusu.
    """
    gecmis = gecmis or []
    arama_sorusu, degisti = soruyu_yeniden_yaz(soru, gecmis)

    parcalar = ara(arama_sorusu, dosyalar)

    if not parcalar:
        return {
            "cevap": "Secili dosyalarda sonuc bulunamadi.",
            "parcalar": [],
            "arama_sorusu": arama_sorusu if degisti else None,
            "kaynaklar": [],
        }

    baglam = "".join(
        f"\n[Parca {i+1} | kaynak: {p['dosya']}]\n{p['metin']}\n"
        for i, p in enumerate(parcalar)
    )

    yanit = ollama.chat(
        model=MODEL_ADI,
        messages=[{"role": "user",
                   "content": SABLON.format(baglam=baglam, soru=arama_sorusu)}],
        options={"temperature": 0.1},
    )

    return {
        "cevap": yanit["message"]["content"],
        "parcalar": parcalar,
        "arama_sorusu": arama_sorusu if degisti else None,
        "kaynaklar": sorted({p["dosya"] for p in parcalar}),
    }