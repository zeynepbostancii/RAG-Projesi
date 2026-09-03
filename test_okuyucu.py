from okuyucular import docx_oku

metin = docx_oku("dokumanlar/test.docx")
print("Karakter sayisi:", len(metin))
print("--- ICERIK ---")
print(metin)