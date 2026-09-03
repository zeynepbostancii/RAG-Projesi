from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

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

pdfler = list(Path("dokumanlar").glob("*.pdf"))
metin = pdf_oku(pdfler[0])
parcalar = parcala(metin)
print("Parca sayisi:", len(parcalar))

model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("Parcalar vektore cevriliyor...")
parca_vektorleri = model.encode(parcalar)
print("Hazir. Boyut:", parca_vektorleri.shape, "\n")

while True:
    soru = input("Soru (cikmak icin bos birak): ")
    if soru.strip() == "":
        break

    soru_vektoru = model.encode([soru])
    skorlar = model.similarity(soru_vektoru, parca_vektorleri)[0]

    sirali = sorted(range(len(skorlar)), key=lambda i: skorlar[i], reverse=True)

    print("\n=== EN IYI 3 PARCA ===")
    for sira, index in enumerate(sirali[:3]):
        print(f"\n[{sira+1}] Parca no: {index} | Skor: {skorlar[index]:.3f}")
        print(parcalar[index][:300].replace("\n", " "))
    print("\n" + "-"*60 + "\n")