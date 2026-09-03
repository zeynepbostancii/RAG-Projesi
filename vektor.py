from sentence_transformers import SentenceTransformer

print("Model indiriliyor / yukleniyor...")
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("Model hazir.\n")

cumleler = [
    "Encapsulation, verilerin disaridan erisime kapatilmasidir.",
    "Data hiding means restricting direct access to fields.",
    "Bugun hava cok guzel, parkta yuruyus yaptim."
]

vektorler = model.encode(cumleler)

print("Vektor boyutu:", vektorler.shape)
print("Ilk cumlenin ilk 10 sayisi:")
print(vektorler[0][:10])
print()

benzerlik = model.similarity(vektorler, vektorler)

print("BENZERLIK TABLOSU (1.00 = ayni, 0.00 = alakasiz)")
for i in range(len(cumleler)):
    for j in range(len(cumleler)):
        if i < j:
            print(f"Cumle {i+1} <-> Cumle {j+1}: {benzerlik[i][j]:.2f}")