from pathlib import Path
from pypdf import PdfReader

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
        bitis = baslangic + parca_boyu
        parca = metin[baslangic:bitis]
        parcalar.append(parca.strip())
        baslangic = baslangic + parca_boyu - bindirme
    return parcalar

pdfler = list(Path("dokumanlar").glob("*.pdf"))
metin = pdf_oku(pdfler[0])

parcalar = parcala(metin)

print("Toplam karakter:", len(metin))
print("Parca sayisi:", len(parcalar))
print()
print("--- 1. PARCA ---")
print(parcalar[0])
print()
print("--- 2. PARCA ---")
print(parcalar[1])