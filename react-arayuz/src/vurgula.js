// Kaynak metinde, cevapla ortusen cumleleri bulup isaretler.
//
// Neden LLM'e sormuyoruz: her cevap icin ek bir model cagrisi demek olurdu,
// CPU'da bu dakikalar ekliyor. Bunun yerine kelime ortusmesine bakiyoruz —
// ucuz ve pratikte yeterince isabetli.

const DURAK = new Set([
  've', 'ile', 'bir', 'bu', 'şu', 'o', 'da', 'de', 'ki', 'için', 'gibi',
  'olarak', 'daha', 'çok', 'en', 'ise', 'ama', 'veya', 'her', 'kadar',
  'sonra', 'önce', 'göre', 'olan', 'olup', 'var', 'yok', 'the', 'and',
  'for', 'that', 'with', 'this', 'from', 'are', 'was', 'has', 'have',
  'not', 'but', 'its', 'his', 'her', 'their', 'been', 'will', 'can',
])

// Noktalama at, kucuk harfe cevir, kisa ve durak kelimeleri ele
function anlamliKelimeler(metin) {
  return new Set(
    metin
      .toLocaleLowerCase('tr')
      .replace(/[^\p{L}\p{N}\s-]/gu, ' ')
      .split(/\s+/)
      .filter((k) => k.length > 3 && !DURAK.has(k))
  )
}

// Sayilar ve kodlar guclu ipucu: 8.400, RISK-014, %61, 22 gibi
function sayiVeKodlar(metin) {
  const bulunan = metin.match(/\b[\p{Lu}]{2,}-?\d+\b|\b\d[\d.,%]*\b/gu) || []
  return new Set(bulunan.map((s) => s.toLocaleLowerCase('tr')))
}

function cumlelereBol(metin) {
  // Satir sonlari ve cumle sonlari birlikte: tablo satirlari ve
  // madde isaretleri de ayri birim sayilsin
  const parcalar = []
  const ham = metin.split(/(?<=[.!?:])\s+|\n+/)
  for (const p of ham) {
    if (p.trim()) parcalar.push(p)
  }
  return parcalar
}

/**
 * Kaynak metni segmentlere böler, hangilerinin vurgulanacağını işaretler.
 * Dönen: [{ metin, vurgulu }]
 */
export function vurguSegmentleri(kaynakMetin, cevapMetni, esik = 0.34) {
  if (!kaynakMetin || !cevapMetni) {
    return [{ metin: kaynakMetin || '', vurgulu: false }]
  }

  const cevapKelime = anlamliKelimeler(cevapMetni)
  const cevapSayi = sayiVeKodlar(cevapMetni)

  if (cevapKelime.size === 0 && cevapSayi.size === 0) {
    return [{ metin: kaynakMetin, vurgulu: false }]
  }

  const cumleler = cumlelereBol(kaynakMetin)
  const segmentler = []
  let imlec = 0

  for (const cumle of cumleler) {
    const yer = kaynakMetin.indexOf(cumle, imlec)
    if (yer === -1) continue

    // Cümleler arası boşlukları koru
    if (yer > imlec) {
      segmentler.push({ metin: kaynakMetin.slice(imlec, yer), vurgulu: false })
    }

    const kelimeler = anlamliKelimeler(cumle)
    const sayilar = sayiVeKodlar(cumle)

    let ortak = 0
    kelimeler.forEach((k) => {
      if (cevapKelime.has(k)) ortak++
    })

    // Sayı veya kod eşleşmesi tek başına güçlü kanıt
    let sayiEslesme = 0
    sayilar.forEach((s) => {
      if (cevapSayi.has(s)) sayiEslesme++
    })

    const oran = kelimeler.size ? ortak / kelimeler.size : 0
    const vurgulu =
      sayiEslesme > 0 || (kelimeler.size >= 3 && oran >= esik)

    segmentler.push({ metin: cumle, vurgulu })
    imlec = yer + cumle.length
  }

  if (imlec < kaynakMetin.length) {
    segmentler.push({ metin: kaynakMetin.slice(imlec), vurgulu: false })
  }

  // Hiçbir şey eşleşmediyse düz metin döndür
  if (!segmentler.some((s) => s.vurgulu)) {
    return [{ metin: kaynakMetin, vurgulu: false }]
  }

  return segmentler
}