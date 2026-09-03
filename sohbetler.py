"""
Sohbet oturumlarini diskte saklar.

Streamlit'in session_state'i sadece tarayici sekmesi acikken yasar.
Uygulama yeniden baslayinca kaybolur. Bu modul sohbetleri JSON dosyasina
yazarak kalici hale getirir.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

DOSYA = Path("./sohbetler.json")


def _oku():
    if not DOSYA.exists():
        return {}
    try:
        return json.loads(DOSYA.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _yaz(veri):
    try:
        DOSYA.write_text(
            json.dumps(veri, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as hata:
        print(f"Sohbet kaydedilemedi: {hata}")


def hepsini_getir():
    """Sohbetleri en yeniden eskiye siralar."""
    veri = _oku()
    return dict(
        sorted(veri.items(), key=lambda x: x[1].get("tarih", ""), reverse=True)
    )


def yeni(ad=None):
    veri = _oku()
    kimlik = str(uuid.uuid4())[:8]
    veri[kimlik] = {
        "ad": ad or "Yeni sohbet",
        "tarih": datetime.now().isoformat(timespec="seconds"),
        "turlar": [],
    }
    _yaz(veri)
    return kimlik


def getir(kimlik):
    return _oku().get(kimlik)


def tur_ekle(kimlik, tur):
    veri = _oku()
    if kimlik not in veri:
        return
    veri[kimlik]["turlar"].append(tur)
    veri[kimlik]["tarih"] = datetime.now().isoformat(timespec="seconds")

    # Ilk soru sohbetin adi olur
    if veri[kimlik]["ad"] == "Yeni sohbet":
        baslik = tur["soru"].strip()
        veri[kimlik]["ad"] = baslik[:40] + ("..." if len(baslik) > 40 else "")

    _yaz(veri)


def sil(kimlik):
    veri = _oku()
    veri.pop(kimlik, None)
    _yaz(veri)


def adlandir(kimlik, ad):
    veri = _oku()
    if kimlik in veri:
        veri[kimlik]["ad"] = ad
        _yaz(veri)