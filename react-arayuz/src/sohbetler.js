// Sohbet oturumlarini tarayicida saklar.
// Not: Bu gercek bir React uygulamasi oldugu icin localStorage kullanilabilir.
// Ileride API'ye tasinirsa sadece bu dosya degisir.

const ANAHTAR = 'bilge.sohbetler'

function oku() {
  try {
    return JSON.parse(localStorage.getItem(ANAHTAR)) || {}
  } catch {
    return {}
  }
}

function yaz(veri) {
  try {
    localStorage.setItem(ANAHTAR, JSON.stringify(veri))
  } catch (e) {
    console.error('Sohbet kaydedilemedi', e)
  }
}

export function hepsi() {
  const veri = oku()
  return Object.entries(veri)
    .map(([id, s]) => ({ id, ...s }))
    .sort((a, b) => (b.tarih || '').localeCompare(a.tarih || ''))
}

export function yeni() {
  const veri = oku()
  const id = Math.random().toString(36).slice(2, 10)
  veri[id] = { ad: 'Yeni sohbet', tarih: new Date().toISOString(), girisler: [] }
  yaz(veri)
  return id
}

export function getir(id) {
  return oku()[id] || null
}

export function girisEkle(id, giris) {
  const veri = oku()
  if (!veri[id]) return
  veri[id].girisler.push(giris)
  veri[id].tarih = new Date().toISOString()
  if (veri[id].ad === 'Yeni sohbet') {
    const b = giris.soru.trim()
    veri[id].ad = b.length > 38 ? b.slice(0, 38) + '…' : b
  }
  yaz(veri)
}

export function sil(id) {
  const veri = oku()
  delete veri[id]
  yaz(veri)
}

export function temizle(id) {
  const veri = oku()
  if (veri[id]) {
    veri[id].girisler = []
    yaz(veri)
  }
}