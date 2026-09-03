from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
client = QdrantClient(path="./vektor_db")

print("Kayitli parca sayisi:", client.count("dokumanlar").count, "\n")

while True:
    soru = input("Soru (cikmak icin bos birak): ")
    if soru.strip() == "":
        break

    soru_vektoru = model.encode(soru).tolist()
    sonuclar = client.query_points(
        collection_name="dokumanlar",
        query=soru_vektoru,
        limit=3,
    ).points

    print()
    for i, s in enumerate(sonuclar):
        print(f"[{i+1}] {s.payload['dosya']} / parca {s.payload['parca_no']} | skor {s.score:.3f}")
        print(s.payload["metin"][:250].replace("\n", " "))
        print()
    print("-"*60 + "\n")