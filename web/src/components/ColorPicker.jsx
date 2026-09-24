import { useState } from 'react'
import { HUE_MAX, HUE_MIN, hexToHsl, hslToHex, readableText } from '../colors'
import { Check } from './Icons'

const LIGHTNESS = [
  { label: 'Foncé', value: 0.36 },
  { label: 'Moyen', value: 0.5 },
  { label: 'Clair', value: 0.64 },
]

// Dégradé de la piste : uniquement les teintes autorisées (le rouge est exclu).
const TRACK = `linear-gradient(to right, ${Array.from({ length: 12 }, (_, index) => {
  const hue = HUE_MIN + ((HUE_MAX - HUE_MIN) * index) / 11
  return `hsl(${hue}, 62%, 50%)`
}).join(', ')})`

/**
 * Sélecteur de couleur : une palette au doigt, plus une teinte libre pour qui
 * veut ajuster. Le rouge n'est jamais proposé, il signale les retards.
 */
export default function ColorPicker({ value, onChange, palette = [] }) {
  const [lightness, setLightness] = useState(0.5)

  // La teinte est lue sur la couleur courante à chaque rendu : le curseur reste
  // aligné avec la pastille choisie, même quand elle vient de la palette.
  const [rawHue] = hexToHsl(value || '#3b82f6')
  const hue = Math.min(HUE_MAX, Math.max(HUE_MIN, Math.round(rawHue)))

  const pickCustom = (nextHue, nextLightness) => {
    setLightness(nextLightness)
    onChange(hslToHex(nextHue, 0.62, nextLightness))
  }

  return (
    <div className="picker">
      <div className="swatches">
        {palette.map((color) => (
          <button
            type="button"
            key={color}
            className={`swatch ${color === value ? 'on' : ''}`}
            style={{ background: color, color: readableText(color) }}
            onClick={() => onChange(color)}
            aria-label={`Couleur ${color}`}
          >
            {color === value && <Check width={16} height={16} />}
          </button>
        ))}
      </div>

      <div className="picker-custom">
        <span className="picker-preview" style={{ background: value }} />
        <input
          type="range"
          min={HUE_MIN}
          max={HUE_MAX}
          value={hue}
          style={{ background: TRACK }}
          onChange={(event) => pickCustom(Number(event.target.value), lightness)}
          aria-label="Teinte"
        />
      </div>

      <div className="segmented small">
        {LIGHTNESS.map((step) => (
          <button
            type="button"
            key={step.label}
            className={lightness === step.value ? 'on' : ''}
            onClick={() => pickCustom(hue, step.value)}
          >
            {step.label}
          </button>
        ))}
      </div>
    </div>
  )
}
