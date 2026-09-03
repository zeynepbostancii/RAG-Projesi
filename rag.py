import ollama
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

MODEL_ADI = "qwen2.5:3b"
KOLEKSIYON = "dokumanlar"

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(path="./vektor_db")

SABLON = SABLON = """Asagidaki metin parcalarini oku ve soruyu cevapla.

Kurallar:
- Cevabini parcalardaki bilgiye dayandir.
- Parcalarda konuyla ilgili hicbir sey yoksa, sadece o zaman "Bu bilgi dokumanlarda bulunmuyor." yaz.
- Parcalarda olmayan kod ornegi veya detay ekleme.
- Kisa ve net yaz. Tekrara girme.
- Kullanicinin dilinde cevapla.

--- PARCALAR ---
{baglam}
--- PARCALAR SONU ---

SORU: {soru}

CEVAP:"""

#Bunların ikisi de 3B modelin sınırı. Notunu al, sunumunda "küçük model talimat takibinde zayıf, üretimde 7B+ gerekli" diye söylersin — ölçüme dayalı bir cümle, değerli.
while True:
    soru = input("\nSoru (cikmak icin bos birak): ")
    if soru.strip() == "":
        break

    sonuclar = client.query_points(
        collection_name=KOLEKSIYON,
        query=model.encode(soru).tolist(),
        limit=4,
    ).points

    baglam = ""
    for i, s in enumerate(sonuclar):
        baglam += f"\n[Parca {i+1} | kaynak: {s.payload['dosya']}]\n{s.payload['metin']}\n"

    print("\nBulunan parcalar:", [f"{s.payload['parca_no']} ({s.score:.2f})" for s in sonuclar])
    print("########## MODELE GIDEN BAGLAM ##########")
    print(baglam)
    print("########## BAGLAM SONU ##########")
    print("Model dusunuyor, bekle...\n")

    cevap = ollama.chat(
        model=MODEL_ADI,
        messages=[{"role": "user", "content": SABLON.format(baglam=baglam, soru=soru)}],
        options={"temperature": 0.1},
    )

    print("=== CEVAP ===")
    print(cevap["message"]["content"])
    print("-" * 60)

client.close()