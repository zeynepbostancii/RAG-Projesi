import uuid
from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

KOLEKSIYON = "dokumanlar"
BOYUT = 384

def pdf_oku(dosya_yolu):
    reader = PdfReader(dosya_yolu)
    metin = ""
    for sayfa in reader.pages:
        icerik = sayfa.extract_text()
        if icerik:
            metin = metin + icerik + "\n"
    return metin

def parcala(metin, parca_boyu=800, bindirme=150):
    parcalar = []
    baslangic = 0
    while baslangic < len(metin):
        parcalar.append(metin[baslangic:baslangic + parca_boyu].strip())
        baslangic = baslangic + parca_boyu - bindirme
    return parcalar

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(path="./vektor_db")

if not client.collection_exists(KOLEKSIYON):
    client.create_collection(
        collection_name=KOLEKSIYON,
        vectors_config=VectorParams(size=BOYUT, distance=Distance.COSINE),
    )
    print("Koleksiyon olusturuldu.")

for pdf in Path("dokumanlar").glob("*.pdf"):
    print("Isleniyor:", pdf.name)
    parcalar = parcala(pdf_oku(pdf))
    vektorler = model.encode(parcalar)

    noktalar = []
    for i, parca in enumerate(parcalar):
        kimlik = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{pdf.name}-{i}"))
        noktalar.append(PointStruct(
            id=kimlik,
            vector=vektorler[i].tolist(),
            payload={"dosya": pdf.name, "parca_no": i, "metin": parca},
        ))

    client.upsert(collection_name=KOLEKSIYON, points=noktalar)
    print(f"  {len(noktalar)} parca kaydedildi.")

print("\nToplam kayit:", client.count(KOLEKSIYON).count)
client.close()