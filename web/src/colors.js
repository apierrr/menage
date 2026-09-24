// Utilitaires de couleur. La règle « pas de rouge » est appliquée des deux
// côtés : ici pour ne pas le proposer, côté serveur pour ne pas l'accepter.

export const OVERDUE = '#dc2626'
export const MINE = '#22c55e'
export const OTHERS = ['#9ca3af', '#6b7280', '#4b5563', '#d1d5db', '#374151', '#e5e7eb']

export function hexToRgb(hex) {
  const value = (hex || '#000000').replace('#', '')
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) || 0)
}

function channel(value) {
  const c = value / 255
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

export function luminance(hex) {
  const [r, g, b] = hexToRgb(hex)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

/** Noir ou blanc, selon ce qui se lit le mieux sur cette couleur. */
export function readableText(hex) {
  const l = luminance(hex)
  const onWhite = 1.05 / (l + 0.05)
  const onBlack = (l + 0.05) / 0.05
  return onBlack > onWhite ? '#0d1117' : '#ffffff'
}

/**
 * Bandes proportionnelles, dans l'ordre reçu : « un tiers ma couleur, deux
 * tiers la sienne ». Les proportions se recalculent depuis les effectifs, pas
 * depuis les pourcentages arrondis du serveur, sinon la dernière bande tombe
 * à côté du bord.
 */
export function splitGradient(parts) {
  const total = parts.reduce((sum, part) => sum + part.count, 0)
  if (!total) return null
  let offset = 0
  const stops = parts.map((part) => {
    const start = offset
    offset += (part.count * 100) / total
    return `${part.color} ${start.toFixed(3)}% ${offset.toFixed(3)}%`
  })
  return `linear-gradient(to right, ${stops.join(', ')})`
}

export function withAlpha(hex, alpha) {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function hslToHex(h, s, l) {
  const a = s * Math.min(l, 1 - l)
  const f = (n) => {
    const k = (n + h / 30) % 12
    const color = l - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)))
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

export function hexToHsl(hex) {
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  if (max === min) return [0, 0, l]
  const d = max - min
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0)
  else if (max === g) h = (b - r) / d + 2
  else h = (r - g) / d + 4
  return [h * 60, s, l]
}

// Teintes interdites : elles sont réservées à l'état « en retard ».
export const HUE_MIN = 14
export const HUE_MAX = 330

export function isReservedRed(hex) {
  const [h, s, l] = hexToHsl(hex)
  if (s < 0.35 || l > 0.82) return false
  return h >= HUE_MAX || h <= HUE_MIN
}
