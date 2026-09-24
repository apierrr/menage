import { useEffect, useState } from 'react'
import ColorPicker from './ColorPicker'
import Sheet from './Sheet'

/** Réglages d'une tuile de profil : le nom et la couleur qui suit la personne partout. */
export default function ProfileForm({ open, profile, palette = [], onClose, onSubmit }) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(palette[0] || '#6366f1')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setName(profile?.name || '')
    setColor(profile?.color || palette[0] || '#6366f1')
    setError(null)
    setSaving(false)
  }, [open, profile])

  const submit = async () => {
    if (!name.trim()) {
      setError('Il faut un prénom.')
      return
    }
    setSaving(true)
    try {
      await onSubmit({ name: name.trim(), color })
      onClose()
    } catch (submitError) {
      setError(submitError.message)
      setSaving(false)
    }
  }

  return (
    <Sheet
      open={open}
      title="Réglages du profil"
      onClose={onClose}
      footer={
        <>
          {error && <p className="form-error">{error}</p>}
          <button type="button" className="btn primary block" disabled={saving} onClick={submit}>
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </>
      }
    >
      <label className="field">
        <span>Prénom</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Alex"
          maxLength={60}
          autoFocus
        />
      </label>

      <div className="field">
        <span>Couleur</span>
        <ColorPicker value={color} onChange={setColor} palette={palette} />
      </div>
    </Sheet>
  )
}
