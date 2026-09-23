// Basit satır içi SVG ikonlar. Ek kütüphane gerektirmez.

const ortak = {
  width: 16,
  height: 16,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

export const Kisi = (p) => (
  <svg {...ortak} {...p}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
)

export const Robot = (p) => (
  <svg {...ortak} {...p}>
    <rect x="4" y="8" width="16" height="12" rx="3" />
    <path d="M12 8V5" />
    <circle cx="12" cy="3.5" r="1.5" />
    <circle cx="9" cy="13.5" r="1" fill="currentColor" stroke="none" />
    <circle cx="15" cy="13.5" r="1" fill="currentColor" stroke="none" />
    <path d="M9.5 17h5" />
  </svg>
)

export const Arti = (p) => (
  <svg {...ortak} {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const Cop = (p) => (
  <svg {...ortak} {...p}>
    <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />
  </svg>
)

export const Gunes = (p) => (
  <svg {...ortak} {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
)

export const Ay = (p) => (
  <svg {...ortak} {...p}>
    <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
  </svg>
)

export const Dosya = (p) => (
  <svg {...ortak} {...p}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
    <path d="M14 3v5h5" />
  </svg>
)

export const Sohbet = (p) => (
  <svg {...ortak} {...p}>
    <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-3.9-.9L3 21l1.9-4.6A8.4 8.4 0 0 1 12 3a8.4 8.4 0 0 1 9 8.5z" />
  </svg>
)

export const Gonder = (p) => (
  <svg {...ortak} {...p}>
    <path d="M4 12h15M13 6l6 6-6 6" />
  </svg>
)

export const Ozet = (p) => (
  <svg {...ortak} {...p}>
    <path d="M4 6h16M4 11h16M4 16h9" />
  </svg>
)

export const Karsilastir = (p) => (
  <svg {...ortak} {...p}>
    <rect x="3" y="4" width="7" height="16" rx="1.5" />
    <rect x="14" y="4" width="7" height="16" rx="1.5" />
    <path d="M10.5 12h3" />
  </svg>
)

export const Ara = (p) => (
  <svg {...ortak} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </svg>
)

export const Yildirim = (p) => (
  <svg {...ortak} {...p}>
    <path d="M13 2L4.5 13H11l-1 9 8.5-11H12l1-9z" />
  </svg>
)

export const Yukle = (p) => (
  <svg {...ortak} {...p}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M7 9l5-5 5 5M12 4v12" />
  </svg>
)

// BTC kurumsal markası — degrade kare üzerinde beyaz harfler.
// Resim yerine SVG: her ekran yoğunluğunda net, tema değişiminden etkilenmez.
export const BtcLogo = ({ boyut = 30 }) => (
  <svg
    width={boyut}
    height={boyut}
    viewBox="0 0 64 64"
    role="img"
    aria-label="BTC"
  >
    <defs>
      <linearGradient id="btc-degrade" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#0A2C5A" />
        <stop offset="100%" stopColor="#1C6DB4" />
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="9" fill="url(#btc-degrade)" />
    <text
      x="32"
      y="41"
      textAnchor="middle"
      fill="#fff"
      fontFamily="'Plus Jakarta Sans', system-ui, sans-serif"
      fontSize="22"
      fontWeight="800"
      fontStyle="italic"
      letterSpacing="-0.5"
    >
      BTC
    </text>
  </svg>
)