from pypdf import PdfReader

reader = PdfReader("dokumanlar/test.pdf")

print("Sayfa sayisi:", len(reader.pages))

metin = ""
for sayfa in reader.pages:
    metin = metin + sayfa.extract_text()

print("Toplam karakter:", len(metin))
print("--- ILK 500 KARAKTER ---")
print(metin[:500])