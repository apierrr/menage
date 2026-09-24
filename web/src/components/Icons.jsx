const base = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

export const Brush = (props) => (
  <svg {...base} {...props}>
    <path d="M9.5 14.5 3 21l6.5-6.5" />
    <path d="M14 4.5 19.5 10 12 17.5 6.5 12z" />
    <path d="m17 2 5 5" />
  </svg>
)

export const Plus = (props) => (
  <svg {...base} {...props}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)

export const Pencil = (props) => (
  <svg {...base} {...props}>
    <path d="M12 20h9" />
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z" />
  </svg>
)

export const Cross = (props) => (
  <svg {...base} {...props}>
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
)

export const Chevron = (props) => (
  <svg {...base} {...props}>
    <path d="m9 18 6-6-6-6" />
  </svg>
)

export const Back = (props) => (
  <svg {...base} {...props}>
    <path d="m15 18-6-6 6-6" />
  </svg>
)

export const Check = (props) => (
  <svg {...base} {...props}>
    <path d="M20 6 9 17l-5-5" />
  </svg>
)

export const Folder = (props) => (
  <svg {...base} {...props}>
    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  </svg>
)

export const Repeat = (props) => (
  <svg {...base} {...props}>
    <path d="m17 2 4 4-4 4" />
    <path d="M3 11v-1a4 4 0 0 1 4-4h14" />
    <path d="m7 22-4-4 4-4" />
    <path d="M21 13v1a4 4 0 0 1-4 4H3" />
  </svg>
)

export const Sparkle = (props) => (
  <svg {...base} {...props}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
    <path d="M7.8 7.8 5 5M16.2 7.8 19 5M7.8 16.2 5 19M16.2 16.2 19 19" />
  </svg>
)
