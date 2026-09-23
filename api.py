"""
RAG API — FastAPI ile HTTP servisi.

Calistirma:
    uvicorn api:app --reload --port 8000

Otomatik dokumantasyon:
    http://localhost:8000/docs
"""

import base64
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import rag_cekirdek as rag


# ---------- Istek ve cevap modelleri ----------
# Pydantic modelleri: gelen body'nin hangi alanlari icermesi gerektigini
# tanimlar. FastAPI bunlari otomatik dogrular ve dokumantasyona yansitir.

class SohbetTuru(BaseModel):
    soru: str
    cevap: str = ""


class SoruIstegi(BaseModel):
    soru: str = Field(..., description="Kullanicinin sorusu")
    dosyalar: list[str] | None = Field(
        None, description="Sadece bu dosyalarda ara. Bos ise hepsinde aranir."
    )
    gecmis: list[SohbetTuru] = Field(
        default_factory=list,
        description="Onceki sohbet turlari. Takip sorulari icin gerekli.",
    )


class Parca(BaseModel):
    dosya: str
    parca_no: int
    metin: str
    vektor_skor: float
    reranker_skor: float | None = None


class CevapYaniti(BaseModel):
    cevap: str
    kaynaklar: list[str]
    arama_sorusu: str | None = None
    parcalar: list[Parca]
    onbellek: bool = Field(
        False, description="Cevap onbellekten mi geldi"
    )


class OzetIstegi(BaseModel):
    dosya: str = Field(..., description="Ozetlenecek dosyanin adi")


class OzetYaniti(BaseModel):
    dosya: str
    ozet: str
    kismi: bool = Field(
        False, description="Dokuman cok uzun oldugu icin ozet kismi mi"
    )
    grup_sayisi: int


class KarsilastirIstegi(BaseModel):
    dosyalar: list[str] = Field(
        ..., min_length=2, max_length=2,
        description="Karsilastirilacak iki dosyanin adi",
    )
    odak: str | None = Field(
        None, description="Karsilastirmada one cikarilacak konu (istege bagli)"
    )


class KarsilastirYaniti(BaseModel):
    dosyalar: list[str]
    karsilastirma: str
    ozetler: dict[str, str]
    kismi: bool = False


class YuklemeYaniti(BaseModel):
    dosya: str
    parca_sayisi: int
    durum: str


class DisKaynakIstegi(BaseModel):
    kaynak_url: str = Field(
        ..., description="Dosyayi base64 olarak donduren web servisin adresi"
    )
    yontem: str = Field("semantik", pattern="^(semantik|sabit)$")
    basliklar: dict[str, str] | None = Field(
        None, description="Kaynak servise gonderilecek ek HTTP basliklari (orn. Authorization)"
    )


# ---------- Uygulama ----------

@asynccontextmanager
async def yasam_dongusu(app: FastAPI):
    # Uygulama acilirken modelleri yukle
    rag.baslat()
    yield
    # Kapanirken veritabani baglantisini kapat
    rag.kapat()


app = FastAPI(
    title="Dokuman Asistani API",
    description="Kurumsal dokumanlar uzerinde soru-cevap servisi",
    version="1.0",
    lifespan=yasam_dongusu,
)


# CORS: tarayici, farkli porttaki servise istek atmayi guvenlik geregi
# engeller. React 5173 portunda, API 8000'de calisacagi icin izin veriyoruz.
# Uretimde "*" yerine sadece gercek arayuz adresi yazilmali.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/saglik", summary="Servis ayakta mi")
def saglik():
    return {"durum": "calisiyor"}


@app.get("/dokumanlar", summary="Yuklu dokumanlari listele")
def dokumanlari_listele():
    dosyalar = rag.dosyalari_listele()
    return {
        "dosyalar": [
            {"ad": ad, "parca_sayisi": adet} for ad, adet in dosyalar.items()
        ],
        "toplam_parca": sum(dosyalar.values()),
    }


@app.post("/dokumanlar", response_model=YuklemeYaniti, summary="Dokuman yukle")
async def dokuman_yukle(
    dosya: UploadFile = File(..., description="PDF, Word, Excel, PowerPoint veya metin"),
    yontem: str = Query("semantik", pattern="^(semantik|sabit)$"),
):
    icerik = await dosya.read()
    adet = rag.dokuman_ekle(dosya.filename, icerik, yontem)

    if adet == -1:
        raise HTTPException(
            status_code=415,
            detail=f"Desteklenmeyen dosya tipi: {dosya.filename}",
        )
    if adet == 0:
        raise HTTPException(
            status_code=422,
            detail="Dosyadan metin cikarilamadi (taranmis PDF olabilir)",
        )

    return YuklemeYaniti(
        dosya=dosya.filename, parca_sayisi=adet, durum="eklendi"
    )


@app.post("/dokumanlar/disardan", response_model=YuklemeYaniti,
          summary="Harici bir web servisten dokuman cek ve ekle")
async def dokuman_disardan_yukle(istek: DisKaynakIstegi):
    """
    Dosya bizim veritabaninda degil, baska bir web servisinde tutuluyorsa
    kullanilir. Servis, dosyayi JSON icinde base64 olarak dondurmeli:

        {"dosya_adi": "rapor.pdf", "icerik_base64": "JVBERi0xLjQK..."}

    Base64 cozulup ayni /dokumanlar akisina (okuma, parcalama, vektorleme,
    kaydetme) sokulur. Yani kaynak fark etmeksizin sonuc ayni sekilde
    aranabilir hale gelir.
    """
    async with httpx.AsyncClient(timeout=30.0) as istemci:
        try:
            yanit = await istemci.get(istek.kaynak_url, headers=istek.basliklar or {})
            yanit.raise_for_status()
        except httpx.HTTPError as hata:
            raise HTTPException(
                status_code=502, detail=f"Kaynak servise ulasilamadi: {hata}"
            )

    try:
        veri = yanit.json()
    except ValueError:
        raise HTTPException(
            status_code=502, detail="Kaynak servis JSON dondurmedi"
        )

    dosya_adi = veri.get("dosya_adi") or veri.get("file_name")
    b64_icerik = veri.get("icerik_base64") or veri.get("file_base64")

    if not dosya_adi or not b64_icerik:
        raise HTTPException(
            status_code=502,
            detail="Kaynak servis 'dosya_adi' ve 'icerik_base64' alanlarini dondurmeli",
        )

    try:
        ikili_veri = base64.b64decode(b64_icerik)
    except Exception:
        raise HTTPException(status_code=400, detail="Gecersiz base64 icerik")

    adet = rag.dokuman_ekle(dosya_adi, ikili_veri, istek.yontem)

    if adet == -1:
        raise HTTPException(
            status_code=415, detail=f"Desteklenmeyen dosya tipi: {dosya_adi}"
        )
    if adet == 0:
        raise HTTPException(
            status_code=422,
            detail="Dosyadan metin cikarilamadi (taranmis PDF olabilir)",
        )

    return YuklemeYaniti(dosya=dosya_adi, parca_sayisi=adet, durum="eklendi")


@app.delete("/dokumanlar/{ad}", summary="Dokuman sil")
def dokuman_sil(ad: str):
    mevcut = rag.dosyalari_listele()
    if ad not in mevcut:
        raise HTTPException(status_code=404, detail=f"Dosya bulunamadi: {ad}")
    rag.dosya_sil(ad)
    return {"dosya": ad, "durum": "silindi"}


@app.post("/ara", summary="Sadece arama yap, cevap uretme")
def arama(istek: SoruIstegi):
    """LLM cagrisi yapmaz. Retrieval kalitesini test etmek icin kullanisli."""
    parcalar = rag.ara(istek.soru, istek.dosyalar)
    return {"soru": istek.soru, "parcalar": parcalar}


@app.post("/sor", response_model=CevapYaniti, summary="Soru sor")
def sor(istek: SoruIstegi):
    if not istek.soru.strip():
        raise HTTPException(status_code=400, detail="Soru bos olamaz")

    gecmis = [t.model_dump() for t in istek.gecmis]
    sonuc = rag.cevapla(istek.soru, istek.dosyalar, gecmis)
    return CevapYaniti(**sonuc)


@app.post("/ozet", response_model=OzetYaniti, summary="Dokuman ozeti cikar")
def ozet(istek: OzetIstegi):
    """
    Dokumanin tamamini isler. RAG aramasindan farkli olarak parca
    secmez, butun metni gruplar halinde ozetleyip birlestirir.
    Uzun dokumanlarda birden fazla LLM cagrisi yapar, sure alabilir.
    """
    mevcut = rag.dosyalari_listele()
    if istek.dosya not in mevcut:
        raise HTTPException(
            status_code=404, detail=f"Dosya bulunamadi: {istek.dosya}"
        )

    sonuc = rag.ozetle(istek.dosya)
    return OzetYaniti(dosya=istek.dosya, **sonuc)


@app.post("/karsilastir", response_model=KarsilastirYaniti,
          summary="Iki dokumani karsilastir")
def karsilastir(istek: KarsilastirIstegi):
    mevcut = rag.dosyalari_listele()
    for ad in istek.dosyalar:
        if ad not in mevcut:
            raise HTTPException(
                status_code=404, detail=f"Dosya bulunamadi: {ad}"
            )

    if istek.dosyalar[0] == istek.dosyalar[1]:
        raise HTTPException(
            status_code=400, detail="Iki farkli dosya secilmeli"
        )

    sonuc = rag.karsilastir(istek.dosyalar[0], istek.dosyalar[1], istek.odak)
    return KarsilastirYaniti(dosyalar=istek.dosyalar, **sonuc)


@app.delete("/onbellek", summary="Cevap onbellegini temizle")
def onbellek_temizle():
    """
    Ayni soruya verilen cevaplar onbellekte tutuluyor. Dokuman eklenip
    silindiginde otomatik temizleniyor, ama elle de bosaltilabilir.
    """
    rag.onbellek_temizle()
    return {"durum": "temizlendi"}