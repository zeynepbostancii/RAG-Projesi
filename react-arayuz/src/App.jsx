import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import * as api from './api'
import * as depo from './sohbetler'
import { vurguSegmentleri } from './vurgula'
import {
  Kisi, Robot, Arti, Cop, Gunes, Ay, Dosya, Sohbet, Gonder, BtcLogo,
  Ozet, Karsilastir, Ara, Yildirim, Yukle,
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
  const [sohbetArama, setSohbetArama] = useState('')

  const [dosyalar, setDosyalar] = useState([])
  const [secili, setSecili] = useState([])
  const [yontem, setYontem] = useState('semantik')
  const [surukleniyor, setSurukleniyor] = useState(false)

  const [soru, setSoru] = useState('')
  // Bekleyen soru ayri tutuluyor: kutu temizlense de ekranda kalsin
  const [bekleyenSoru, setBekleyenSoru] = useState(null)
  const [yukleniyor, setYukleniyor] = useState(false)
  const [hata, setHata] = useState(null)
  const [acikKaynak, setAcikKaynak] = useState({})
  const [analizOdak, setAnalizOdak] = useState('')

  const dosyaSecici = useRef(null)
  const akisSonu = useRef(null)

  const bekliyor = bekleyenSoru !== null

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
  }, [girisler.length, bekleyenSoru])

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
      if (kalan.length) sohbetAc(kalan[0].id)
      else sohbetYeni()
    }
  }

  // Sohbet araması: hem başlıkta hem soru/cevap metinlerinde arıyor
  const suzulmusSohbetler = useMemo(() => {
    const q = sohbetArama.trim().toLocaleLowerCase('tr')
    if (!q) return sohbetler

    return sohbetler.filter((s) => {
      if (s.ad.toLocaleLowerCase('tr').includes(q)) return true
      return (s.girisler || []).some(
        (g) =>
          g.soru?.toLocaleLowerCase('tr').includes(q) ||
          g.cevap?.toLocaleLowerCase('tr').includes(q)
      )
    })
  }, [sohbetler, sohbetArama])

  // --- Dosya islemleri ---
  async function dosyalariIsle(secilenler) {
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

  function dosyaSecildi(olay) {
    dosyalariIsle(Array.from(olay.target.files))
  }

  function birakildi(olay) {
    olay.preventDefault()
    setSurukleniyor(false)
    dosyalariIsle(Array.from(olay.dataTransfer.files))
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

  // --- Dokuman analizi ---
  async function analizCalistir(tur) {
    if (bekliyor) return

    if (tur === 'ozet' && secili.length !== 1) {
      setHata('Özet için tam olarak bir doküman seçin.')
      return
    }
    if (tur === 'karsilastir' && secili.length !== 2) {
      setHata('Karşılaştırma için tam olarak iki doküman seçin.')
      return
    }

    const baslik =
      tur === 'ozet'
        ? `${secili[0]} dokümanının özeti`
        : `${secili[0]} ile ${secili[1]} karşılaştırması` +
          (analizOdak.trim() ? ` — ${analizOdak.trim()}` : '')

    setHata(null)
    setBekleyenSoru(baslik)

    try {
      let cevap, ek
      if (tur === 'ozet') {
        const veri = await api.ozet(secili[0])
        cevap = veri.ozet
        ek = veri.kismi ? 'Doküman uzun olduğu için özet ilk bölümleri kapsıyor.' : null
      } else {
        const veri = await api.karsilastir(secili, analizOdak)
        cevap = veri.karsilastirma
        ek = veri.kismi ? 'Dokümanlar uzun olduğu için karşılaştırma ilk bölümleri kapsıyor.' : null
      }

      const giris = {
        soru: baslik, cevap, kaynaklar: [...secili], parcalar: [],
        arama_sorusu: null, analiz: true, uyari: ek,
      }
      setGirisler((o) => [...o, giris])
      depo.girisEkle(aktifId, giris)
      setSohbetler(depo.hepsi())
      setAnalizOdak('')
    } catch (e) {
      setHata(e.message)
    } finally {
      setBekleyenSoru(null)
    }
  }

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
    setBekleyenSoru(metin)   // soru hemen ekranda görünsün

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
      setSoru(metin)         // hata olursa soru kutuya geri gelsin
    } finally {
      setBekleyenSoru(null)
    }
  }

  const meshZemin = (
    <div className="mesh-zemin" aria-hidden="true">
      <span /><span /><span />
    </div>
  )

  // --- Durum ekranlari ---
  if (baglanti === 'kontrol') {
    return (
      <>
        {meshZemin}
        <div className="durum">
          <div className="durum-marka">
            <div className="logo-halka"><BtcLogo boyut={44} /></div>
            <div>
              <div className="marka-buyuk">{AD}</div>
              <div className="marka-slogan">{SLOGAN}</div>
            </div>
          </div>
          <p>Servise bağlanılıyor…</p>
        </div>
      </>
    )
  }

  if (baglanti === 'kapali') {
    return (
      <>
        {meshZemin}
        <div className="durum">
          <div className="durum-marka">
            <div className="logo-halka"><BtcLogo boyut={44} /></div>
            <div>
              <div className="marka-buyuk">{AD}</div>
              <div className="marka-slogan">{SLOGAN}</div>
            </div>
          </div>
          <h2>Servis çalışmıyor</h2>
          <p>Bir terminalde şunu çalıştırıp sayfayı yenileyin.</p>
          <code>uvicorn api:app --port 8000</code>
        </div>
      </>
    )
  }

  const toplamParca = dosyalar.reduce((t, d) => t + d.parca_sayisi, 0)

  return (
    <>
    {meshZemin}
    <div className="duzen">
      {/* ---------------- Kenar çubuğu ---------------- */}
      <aside className="kenar">
        <div className="marka">
          <div className="logo-halka"><BtcLogo boyut={38} /></div>
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
            {dosyalar.length > 0 && <span className="rozet">{dosyalar.length}</span>}
          </button>
        </div>

        <div className="sekme-icerik">
          {sekme === 'sohbetler' && (
            <>
              <div className="arama-kutusu">
                <Ara width={14} height={14} />
                <input
                  value={sohbetArama}
                  onChange={(e) => setSohbetArama(e.target.value)}
                  placeholder="Sohbetlerde ara"
                  aria-label="Sohbetlerde ara"
                />
                {sohbetArama && (
                  <button
                    className="arama-temizle"
                    onClick={() => setSohbetArama('')}
                    aria-label="Aramayı temizle"
                  >
                    ×
                  </button>
                )}
              </div>

              <div className="sohbet-listesi">
                {suzulmusSohbetler.length === 0 && (
                  <p className="bos-not">
                    {sohbetArama ? 'Eşleşen sohbet yok.' : 'Henüz sohbet yok.'}
                  </p>
                )}
                {suzulmusSohbetler.map((s) => (
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
                    >
                      <Cop width={14} height={14} />
                    </button>
                  </div>
                ))}
              </div>
            </>
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

              <label
                className={`birak-alani${surukleniyor ? ' aktif' : ''}${yukleniyor ? ' mesgul' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setSurukleniyor(true) }}
                onDragLeave={() => setSurukleniyor(false)}
                onDrop={birakildi}
              >
                <input
                  ref={dosyaSecici}
                  type="file"
                  multiple
                  accept=".pdf,.docx,.xlsx,.pptx,.txt,.md"
                  onChange={dosyaSecildi}
                  disabled={yukleniyor}
                />
                <span className="birak-ikon">
                  <Yukle width={20} height={20} />
                </span>
                <span className="birak-baslik">
                  {yukleniyor ? 'İşleniyor…' : 'Doküman ekle'}
                </span>
                <span className="birak-alt">
                  {yukleniyor ? 'Lütfen bekleyin' : 'Sürükleyin veya tıklayın'}
                </span>
                <span className="birak-tipler">PDF · Word · Excel · PPT · TXT</span>
              </label>

              {dosyalar.length === 0 ? (
                <p className="bos-not">Arşiv boş. İlk dokümanı ekleyin.</p>
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
                        <label htmlFor={`d-${d.ad}`} title={d.ad}>{d.ad}</label>
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

                  <div className="analiz">
                    <p className="analiz-baslik">Doküman analizi</p>
                    <input
                      className="odak-kutusu"
                      value={analizOdak}
                      onChange={(e) => setAnalizOdak(e.target.value)}
                      placeholder="Odak konusu (isteğe bağlı)"
                      disabled={bekliyor}
                    />
                    <div className="analiz-dugmeler">
                      <button
                        onClick={() => analizCalistir('ozet')}
                        disabled={bekliyor || secili.length !== 1}
                      >
                        <Ozet width={14} height={14} />
                        Özetle
                      </button>
                      <button
                        onClick={() => analizCalistir('karsilastir')}
                        disabled={bekliyor || secili.length !== 2}
                      >
                        <Karsilastir width={14} height={14} />
                        Karşılaştır
                      </button>
                    </div>
                    <p className="analiz-not">
                      {secili.length === 1
                        ? 'Özet için hazır. Karşılaştırma iki doküman ister.'
                        : secili.length === 2
                          ? 'Karşılaştırma için hazır.'
                          : `${secili.length} doküman seçili.`}
                    </p>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        <div className="kenar-alt">
          <button
            className="tema-dugme"
            onClick={() => setTema(tema === 'acik' ? 'koyu' : 'acik')}
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
                yazar. Kaynağa tıklayınca kullanılan cümleler işaretli görünür.
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
                <div className={`balon asistan-balon${g.analiz ? ' analiz-balon' : ''}`}>
                  {g.analiz && (
                    <p className="analiz-etiket">
                      Doküman analizi · {g.kaynaklar?.join(' · ')}
                    </p>
                  )}

                  <p className="cevap">{g.cevap}</p>
                  {g.uyari && <p className="analiz-uyari">{g.uyari}</p>}

                  {g.onbellek && (
                    <p className="onbellek-not">
                      <Yildirim width={12} height={12} />
                      Daha önce sorulmuştu, kayıtlı cevap kullanıldı
                    </p>
                  )}

                  {g.arama_sorusu && (
                    <p className="arama-notu">
                      Arama: <span>{g.arama_sorusu}</span>
                    </p>
                  )}

                  {g.parcalar?.length > 0 && (
                    <div className="kaynaklar">
                      <p className="kaynak-baslik">
                        Kaynaklar — kullanılan cümleler işaretlidir
                      </p>
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
                                <span className="kaynak-skor">{skor.toFixed(2)}</span>
                              </button>
                              {acik && (
                                <div className="kaynak-metin">
                                  {vurguSegmentleri(p.metin, g.cevap).map((s, k) =>
                                    s.vurgulu ? (
                                      <mark key={k}>{s.metin}</mark>
                                    ) : (
                                      <span key={k}>{s.metin}</span>
                                    )
                                  )}
                                </div>
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

          {/* Bekleyen soru: kutu temizlense de ekranda kalıyor */}
          {bekliyor && (
            <div className="tur">
              <div className="mesaj kullanici">
                <div className="avatar kullanici-avatar">
                  <Kisi width={15} height={15} />
                </div>
                <div className="balon kullanici-balon">{bekleyenSoru}</div>
              </div>

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
    </>
  )
}