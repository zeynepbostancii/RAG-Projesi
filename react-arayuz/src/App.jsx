import { useState, useEffect, useRef, useCallback } from 'react'
import * as api from './api'
import * as depo from './sohbetler'
import {
  Kisi, Robot, Arti, Cop, Gunes, Ay, Dosya, Sohbet, Gonder, BtcLogo,
} from './ikonlar'

const TEMA_ANAHTARI = 'bilge.tema'
const AD = 'Bilge'
const SLOGAN = 'Kurumsal hafızanız'

export default function App() {
  const [tema, setTema] = useState(
    () => localStorage.getItem(TEMA_ANAHTARI) || 'acik'
  )
  const [sekme, setSekme] = useState('sohbetler')
  const [baglanti, setBaglanti] = useState('kontrol')

  const [sohbetler, setSohbetler] = useState([])
  const [aktifId, setAktifId] = useState(null)
  const [girisler, setGirisler] = useState([])

  const [dosyalar, setDosyalar] = useState([])
  const [secili, setSecili] = useState([])
  const [yontem, setYontem] = useState('semantik')

  const [soru, setSoru] = useState('')
  const [bekliyor, setBekliyor] = useState(false)
  const [yukleniyor, setYukleniyor] = useState(false)
  const [hata, setHata] = useState(null)
  const [acikKaynak, setAcikKaynak] = useState({})

  const dosyaSecici = useRef(null)
  const akisSonu = useRef(null)

  // --- Tema ---
  useEffect(() => {
    document.documentElement.dataset.tema = tema
    localStorage.setItem(TEMA_ANAHTARI, tema)
  }, [tema])

  // --- Acilis ---
  useEffect(() => {
    const liste = depo.hepsi()
    if (liste.length === 0) {
      const id = depo.yeni()
      setSohbetler(depo.hepsi())
      setAktifId(id)
    } else {
      setSohbetler(liste)
      setAktifId(liste[0].id)
      setGirisler(liste[0].girisler || [])
    }

    api.saglik()
      .then(() => {
        setBaglanti('acik')
        return dosyalariTazele()
      })
      .catch(() => setBaglanti('kapali'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    akisSonu.current?.scrollIntoView({ block: 'end' })
  }, [girisler.length, bekliyor])

  async function dosyalariTazele() {
    const veri = await api.dokumanlariGetir()
    setDosyalar(veri.dosyalar)
    setSecili(veri.dosyalar.map((d) => d.ad))
  }

  // --- Sohbet islemleri ---
  function sohbetAc(id) {
    setAktifId(id)
    setGirisler(depo.getir(id)?.girisler || [])
    setAcikKaynak({})
    setHata(null)
  }

  function sohbetYeni() {
    const id = depo.yeni()
    setSohbetler(depo.hepsi())
    setAktifId(id)
    setGirisler([])
    setAcikKaynak({})
  }

  function sohbetSil(id, olay) {
    olay.stopPropagation()
    depo.sil(id)
    const kalan = depo.hepsi()
    setSohbetler(kalan)
    if (id === aktifId) {
      if (kalan.length) {
        sohbetAc(kalan[0].id)
      } else {
        sohbetYeni()
      }
    }
  }

  // --- Dosya islemleri ---
  async function dosyaYukle(olay) {
    const secilenler = Array.from(olay.target.files)
    if (!secilenler.length) return

    setYukleniyor(true)
    setHata(null)
    const yeniler = []

    for (const dosya of secilenler) {
      try {
        await api.dokumanYukle(dosya, yontem)
        yeniler.push(dosya.name)
      } catch (e) {
        setHata(`${dosya.name} işlenemedi: ${e.message}`)
      }
    }

    const veri = await api.dokumanlariGetir()
    setDosyalar(veri.dosyalar)
    if (yeniler.length) setSecili(yeniler)

    setYukleniyor(false)
    if (dosyaSecici.current) dosyaSecici.current.value = ''
  }

  async function dosyaKaldir(ad) {
    await api.dokumanSil(ad)
    const veri = await api.dokumanlariGetir()
    setDosyalar(veri.dosyalar)
    setSecili((o) => o.filter((d) => d !== ad))
  }

  function secimDegistir(ad) {
    setSecili((o) => (o.includes(ad) ? o.filter((d) => d !== ad) : [...o, ad]))
  }

  const kaynakAcKapa = useCallback((i, j) => {
    const a = `${i}-${j}`
    setAcikKaynak((o) => ({ ...o, [a]: !o[a] }))
  }, [])

  // --- Soru gonderme ---
  async function gonder(olay) {
    olay.preventDefault()
    const metin = soru.trim()
    if (!metin || bekliyor) return

    if (!secili.length) {
      setHata('Arama yapmak için en az bir doküman seçin.')
      return
    }

    setSoru('')
    setHata(null)
    setBekliyor(true)

    const gecmis = girisler.map((g) => ({ soru: g.soru, cevap: g.cevap }))
    const hepsiSecili = secili.length === dosyalar.length

    try {
      const veri = await api.sor(metin, hepsiSecili ? null : secili, gecmis)
      const giris = { soru: metin, ...veri }
      setGirisler((o) => [...o, giris])
      depo.girisEkle(aktifId, giris)
      setSohbetler(depo.hepsi())
    } catch (e) {
      setHata(e.message)
    } finally {
      setBekliyor(false)
    }
  }

  // --- Durum ekranlari ---
  if (baglanti === 'kontrol') {
    return (
      <div className="durum">
        <div className="durum-marka">
          <BtcLogo boyut={44} />
          <div>
            <div className="marka-buyuk">{AD}</div>
            <div className="marka-slogan">{SLOGAN}</div>
          </div>
        </div>
        <p>Servise bağlanılıyor…</p>
      </div>
    )
  }

  if (baglanti === 'kapali') {
    return (
      <div className="durum">
        <div className="durum-marka">
          <BtcLogo boyut={44} />
          <div>
            <div className="marka-buyuk">{AD}</div>
            <div className="marka-slogan">{SLOGAN}</div>
          </div>
        </div>
        <h2>Servis çalışmıyor</h2>
        <p>Bir terminalde şunu çalıştırıp sayfayı yenileyin.</p>
        <code>uvicorn api:app --port 8000</code>
      </div>
    )
  }

  const toplamParca = dosyalar.reduce((t, d) => t + d.parca_sayisi, 0)

  return (
    <div className="duzen">
      {/* ---------------- Kenar çubuğu ---------------- */}
      <aside className="kenar">
        <div className="marka">
          <BtcLogo boyut={50} />
          <div className="marka-yazi">
            <span className="marka-ad">{AD}</span>
            <span className="marka-slogan">{SLOGAN}</span>
          </div>
        </div>

        <button className="yeni-sohbet" onClick={sohbetYeni}>
          <Arti width={15} height={15} />
          Yeni sohbet
        </button>

        <div className="sekmeler" role="tablist">
          <button
            role="tab"
            aria-selected={sekme === 'sohbetler'}
            onClick={() => setSekme('sohbetler')}
          >
            <Sohbet width={14} height={14} />
            Sohbetler
          </button>
          <button
            role="tab"
            aria-selected={sekme === 'arsiv'}
            onClick={() => setSekme('arsiv')}
          >
            <Dosya width={14} height={14} />
            Arşiv
            {dosyalar.length > 0 && (
              <span className="rozet">{dosyalar.length}</span>
            )}
          </button>
        </div>

        <div className="sekme-icerik">
          {sekme === 'sohbetler' && (
            <div className="sohbet-listesi">
              {sohbetler.map((s) => (
                <div
                  key={s.id}
                  className={`sohbet-satir${s.id === aktifId ? ' aktif' : ''}`}
                  onClick={() => sohbetAc(s.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && sohbetAc(s.id)}
                >
                  <span className="sohbet-ad">{s.ad}</span>
                  <button
                    className="sohbet-sil"
                    onClick={(e) => sohbetSil(s.id, e)}
                    aria-label="Sohbeti sil"
                    title="Sil"
                  >
                    <Cop width={14} height={14} />
                  </button>
                </div>
              ))}
            </div>
          )}

          {sekme === 'arsiv' && (
            <div className="arsiv">
              <div className="yontem" role="group" aria-label="Parçalama yöntemi">
                <button
                  aria-pressed={yontem === 'semantik'}
                  onClick={() => setYontem('semantik')}
                >
                  Anlama göre
                </button>
                <button
                  aria-pressed={yontem === 'sabit'}
                  onClick={() => setYontem('sabit')}
                >
                  Sabit boy
                </button>
              </div>

              <label className="yukle">
                <input
                  ref={dosyaSecici}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.xlsx,.pptx,.txt,.md"
                  onChange={dosyaYukle}
                  disabled={yukleniyor}
                />
                <span>{yukleniyor ? 'İşleniyor…' : 'Doküman ekle'}</span>
              </label>

              {dosyalar.length === 0 ? (
                <p className="bos-not">
                  PDF, Word, Excel, PowerPoint veya metin dosyası ekleyin.
                </p>
              ) : (
                <>
                  <div className="dosya-listesi">
                    {dosyalar.map((d) => (
                      <div key={d.ad} className="dosya-satir">
                        <input
                          id={`d-${d.ad}`}
                          type="checkbox"
                          checked={secili.includes(d.ad)}
                          onChange={() => secimDegistir(d.ad)}
                        />
                        <label htmlFor={`d-${d.ad}`} title={d.ad}>
                          {d.ad}
                        </label>
                        <span className="parca-sayi">{d.parca_sayisi}</span>
                        <button
                          className="dosya-sil"
                          onClick={() => dosyaKaldir(d.ad)}
                          aria-label={`${d.ad} kaldır`}
                        >
                          <Cop width={13} height={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    className="metin-buton"
                    onClick={() => setSecili(dosyalar.map((d) => d.ad))}
                    disabled={secili.length === dosyalar.length}
                  >
                    Tümünü seç
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        <div className="kenar-alt">
          <button
            className="tema-dugme"
            onClick={() => setTema(tema === 'acik' ? 'koyu' : 'acik')}
            aria-label="Temayı değiştir"
          >
            {tema === 'acik' ? <Ay width={15} height={15} /> : <Gunes width={15} height={15} />}
            {tema === 'acik' ? 'Karanlık tema' : 'Aydınlık tema'}
          </button>
          <span className="kenar-bilgi">{toplamParca} parça indekslendi</span>
        </div>
      </aside>

      {/* ---------------- Sohbet ---------------- */}
      <main className="ana">
        <header className="ust">
          <h1>{depo.getir(aktifId)?.ad || 'Yeni sohbet'}</h1>
          <span className="kapsam">
            {dosyalar.length === 0
              ? 'arşiv boş'
              : secili.length === dosyalar.length
                ? `${dosyalar.length} doküman`
                : `${secili.length}/${dosyalar.length} doküman`}
          </span>
        </header>

        <div className="akis">
          {girisler.length === 0 && !bekliyor && (
            <div className="karsilama">
              <BtcLogo boyut={46} />
              <p className="karsilama-baslik">Dokümanlarınıza soru sorun</p>
              <p className="karsilama-alt">
                Her cevabın altında hangi dosyanın hangi parçasından geldiği
                yazar. İstediğiniz kaynağa tıklayıp metnin aslını görebilirsiniz.
              </p>
              <div className="ornekler">
                <span>Örnek</span>
                <em>Yıllık izin talebi kaç gün önceden yapılmalı?</em>
              </div>
            </div>
          )}

          {girisler.map((g, i) => (
            <div className="tur" key={i}>
              <div className="mesaj kullanici">
                <div className="avatar kullanici-avatar">
                  <Kisi width={15} height={15} />
                </div>
                <div className="balon kullanici-balon">{g.soru}</div>
              </div>

              <div className="mesaj asistan">
                <div className="avatar asistan-avatar">
                  <Robot width={15} height={15} />
                </div>
                <div className="balon asistan-balon">
                  <p className="cevap">{g.cevap}</p>

                  {g.arama_sorusu && (
                    <p className="arama-notu">
                      Arama: <span>{g.arama_sorusu}</span>
                    </p>
                  )}

                  {g.parcalar?.length > 0 && (
                    <div className="kaynaklar">
                      <p className="kaynak-baslik">Kaynaklar</p>
                      <ul>
                        {g.parcalar.map((p, j) => {
                          const acik = !!acikKaynak[`${i}-${j}`]
                          const skor =
                            p.reranker_skor !== null && p.reranker_skor !== undefined
                              ? p.reranker_skor
                              : p.vektor_skor
                          return (
                            <li key={j}>
                              <button
                                className="kaynak-ozet"
                                onClick={() => kaynakAcKapa(i, j)}
                                aria-expanded={acik}
                              >
                                <span className="kaynak-no">{j + 1}</span>
                                <span className="kaynak-dosya">
                                  {p.dosya} · parça {p.parca_no}
                                </span>
                                <span className="kaynak-skor">
                                  {skor.toFixed(2)}
                                </span>
                              </button>
                              {acik && (
                                <div className="kaynak-metin">{p.metin}</div>
                              )}
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {bekliyor && (
            <div className="mesaj asistan">
              <div className="avatar asistan-avatar">
                <Robot width={15} height={15} />
              </div>
              <div className="balon asistan-balon dusunuyor">
                Düşünüyorum
                <span className="nokta n1" />
                <span className="nokta n2" />
                <span className="nokta n3" />
              </div>
            </div>
          )}

          <div ref={akisSonu} />
        </div>

        {hata && <div className="hata">{hata}</div>}

        <form onSubmit={gonder} className="soru-alani">
          <input
            value={soru}
            onChange={(e) => setSoru(e.target.value)}
            placeholder="Ne öğrenmek istiyorsunuz?"
            disabled={bekliyor}
            aria-label="Soru"
          />
          <button type="submit" disabled={bekliyor || !soru.trim()}>
            <Gonder width={16} height={16} />
          </button>
        </form>
      </main>
    </div>
  )
}