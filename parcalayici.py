"""
Metin parcalama yontemleri.

sabit_parcala   : eski yontem, belirli karakter sayisina gore boler
semantik_parcala: cumleler arasi anlam benzerligine gore boler
"""

import re

import numpy as np


def sabit_parcala(metin, parca_boyu=800, bindirme=150):
    """Sabit karakter sayisina gore boler. Anlama bakmaz."""
    parcalar, baslangic = [], 0
    while baslangic < len(metin):
        parcalar.append(metin[baslangic:baslangic + parca_boyu].strip())
        baslangic += parca_boyu - bindirme
    return [p for p in parcalar if p]


def _birimlere_ayir(metin):
    """
    Metni cumle/satir birimlerine ayirir.

    Once satirlara boluyoruz cunku tablo satirlari, slayt basliklari ve
    madde isaretleri zaten anlamli birimler. Uzun satirlari ayrica
    cumlelere boluyoruz.
    """
    birimler = []

    for satir in metin.split("\n"):
        satir = satir.strip()
        if not satir:
            continue

        # Kisa satirlar (baslik, tablo satiri, madde) tek birim kalir
        if len(satir) < 150:
            birimler.append(satir)
            continue

        # Uzun satirlari cumlelere bol
        cumleler = re.split(r"(?<=[.!?:])\s+(?=[A-ZÇĞİÖŞÜ0-9])", satir)
        for c in cumleler:
            c = c.strip()
            if c:
                birimler.append(c)

    return birimler


def semantik_parcala(
    metin,
    model,
    esik_yuzdelik=90,
    min_boyut=200,
    max_boyut=1600,
    pencere=1,
):
    """
    Metni anlam benzarligine gore boler.

    Mantik: ardisik birimleri vektore cevirir, komsu birimler arasindaki
    benzerlige bakar. Benzerlik aniden dustugu yer konu degisimidir,
    kesim noktasi orasidir.

    esik_yuzdelik : kacinci yuzdelikteki dusus kesim sayilir (90 = en keskin %10)
    min_boyut     : bundan kucuk parcalar bir sonrakiyle birlestirilir
    max_boyut     : bundan buyuk parcalar zorla bolunur
    pencere       : karsilastirmada kac komsu birim birlikte degerlendirilir
    """
    birimler = _birimlere_ayir(metin)

    if len(birimler) <= 1:
        return [metin.strip()] if metin.strip() else []

    # Her birimi komsulariyla birlikte vektore cevir (baglam korunsun diye)
    baglamli = []
    for i in range(len(birimler)):
        bas = max(0, i - pencere)
        son = min(len(birimler), i + pencere + 1)
        baglamli.append(" ".join(birimler[bas:son]))

    vektorler = model.encode(baglamli, show_progress_bar=False)
    vektorler = np.asarray(vektorler, dtype=np.float32)

    # Kosinus benzerligi icin normalize et
    normlar = np.linalg.norm(vektorler, axis=1, keepdims=True)
    normlar[normlar == 0] = 1e-9
    birim_vek = vektorler / normlar

    # Komsu birimler arasindaki uzaklik (1 - benzerlik)
    benzerlikler = np.sum(birim_vek[:-1] * birim_vek[1:], axis=1)
    uzakliklar = 1.0 - benzerlikler

    if len(uzakliklar) == 0:
        return [metin.strip()]

    esik = float(np.percentile(uzakliklar, esik_yuzdelik))

    # Kesim noktalarini belirle
    kesimler = [0]
    for i, u in enumerate(uzakliklar):
        if u > esik:
            kesimler.append(i + 1)
    kesimler.append(len(birimler))

    # Parcalari olustur
    ham_parcalar = []
    for i in range(len(kesimler) - 1):
        grup = birimler[kesimler[i]:kesimler[i + 1]]
        if grup:
            ham_parcalar.append("\n".join(grup))

    # Cok kucuk parcalari birlestir
    birlesik = []
    tampon = ""
    for p in ham_parcalar:
        if tampon:
            aday = tampon + "\n" + p
        else:
            aday = p

        if len(aday) < min_boyut:
            tampon = aday
        else:
            birlesik.append(aday)
            tampon = ""
    if tampon:
        if birlesik:
            birlesik[-1] = birlesik[-1] + "\n" + tampon
        else:
            birlesik.append(tampon)

    # Cok buyuk parcalari zorla bol
    sonuc = []
    for p in birlesik:
        if len(p) <= max_boyut:
            sonuc.append(p)
        else:
            sonuc.extend(sabit_parcala(p, parca_boyu=max_boyut, bindirme=150))

    return [p.strip() for p in sonuc if p.strip()]