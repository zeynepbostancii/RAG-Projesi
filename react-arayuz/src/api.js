// API ile konusan tek dosya. Tum HTTP cagrilari burada toplanir.
// Boylece adres degisirse tek yerden guncellenir.

const API = 'http://localhost:8000'

async function istek(yol, secenekler = {}) {
  const cevap = await fetch(`${API}${yol}`, secenekler)
  if (!cevap.ok) {
    const hata = await cevap.json().catch(() => ({}))
    throw new Error(hata.detail || `Hata ${cevap.status}`)
  }
  return cevap.json()
}

export const saglik = () => istek('/saglik')

export const dokumanlariGetir = () => istek('/dokumanlar')

export const dokumanYukle = (dosya, yontem = 'semantik') => {
  const form = new FormData()
  form.append('dosya', dosya)
  return istek(`/dokumanlar?yontem=${yontem}`, { method: 'POST', body: form })
}

export const dokumanSil = (ad) =>
  istek(`/dokumanlar/${encodeURIComponent(ad)}`, { method: 'DELETE' })

export const sor = (soru, dosyalar, gecmis) =>
  istek('/sor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ soru, dosyalar, gecmis }),
  })

export const ozet = (dosya) =>
  istek('/ozet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dosya }),
  })

export const karsilastir = (dosyalar, odak) =>
  istek('/karsilastir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dosyalar, odak: odak || null }),
  })