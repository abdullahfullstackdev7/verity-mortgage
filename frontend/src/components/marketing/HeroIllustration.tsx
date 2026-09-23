export function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 480 420"
      fill="none"
      className="w-full max-w-md drop-shadow-xl"
      role="img"
      aria-label="Illustration of a document being verified against application data"
    >
      <defs>
        <linearGradient id="hero-navy" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#16244a" />
          <stop offset="1" stopColor="#0b1b36" />
        </linearGradient>
        <linearGradient id="hero-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#e3b768" />
          <stop offset="1" stopColor="#b8863b" />
        </linearGradient>
      </defs>

      {/* back document */}
      <rect
        x="72"
        y="48"
        width="230"
        height="300"
        rx="16"
        fill="#eef1f5"
        stroke="#e3e1d9"
        transform="rotate(-6 72 48)"
      />

      {/* middle document */}
      <rect
        x="118"
        y="36"
        width="230"
        height="300"
        rx="16"
        fill="#ffffff"
        stroke="#e3e1d9"
        transform="rotate(4 118 36)"
      />
      <g transform="rotate(4 118 36)" opacity="0.7">
        <rect x="140" y="70" width="140" height="10" rx="5" fill="#c8cdd6" />
        <rect x="140" y="94" width="170" height="8" rx="4" fill="#dde1e7" />
        <rect x="140" y="112" width="170" height="8" rx="4" fill="#dde1e7" />
        <rect x="140" y="130" width="110" height="8" rx="4" fill="#dde1e7" />
        <rect x="140" y="168" width="90" height="8" rx="4" fill="#dde1e7" />
        <rect x="140" y="186" width="170" height="8" rx="4" fill="#dde1e7" />
        <rect x="140" y="204" width="150" height="8" rx="4" fill="#dde1e7" />
      </g>

      {/* front navy document (the "stated application") */}
      <rect x="90" y="86" width="230" height="300" rx="16" fill="url(#hero-navy)" />
      <g opacity="0.85">
        <rect x="118" y="122" width="130" height="12" rx="6" fill="#f4f2ea" opacity="0.9" />
        <rect x="118" y="150" width="174" height="8" rx="4" fill="#8b97b3" />
        <rect x="118" y="168" width="174" height="8" rx="4" fill="#8b97b3" />
        <rect x="118" y="186" width="120" height="8" rx="4" fill="#8b97b3" />

        <rect x="118" y="222" width="90" height="8" rx="4" fill="#63719a" />
        <rect x="118" y="240" width="174" height="8" rx="4" fill="#8b97b3" />
        <rect x="118" y="258" width="150" height="8" rx="4" fill="#8b97b3" />

        <rect x="118" y="294" width="70" height="8" rx="4" fill="#63719a" />
        <rect x="118" y="312" width="174" height="8" rx="4" fill="#8b97b3" />
        <rect x="118" y="330" width="140" height="8" rx="4" fill="#8b97b3" />
      </g>

      {/* verification badge */}
      <circle cx="336" cy="300" r="54" fill="url(#hero-gold)" />
      <circle cx="336" cy="300" r="54" fill="none" stroke="#fbfaf7" strokeWidth="4" />
      <path
        d="M312 300l17 17 34-34"
        stroke="#1b1400"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  )
}
