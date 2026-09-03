"""
RAG API — FastAPI ile HTTP servisi.

Calistirma:
    uvicorn api:app --reload --port 8000

Otomatik dokumantasyon:
    http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

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


class YuklemeYaniti(BaseModel):
    dosya: str
    parca_sayisi: int
    durum: str


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