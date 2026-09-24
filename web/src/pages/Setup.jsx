import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import ProfileForm from '../components/ProfileForm'
import ProfileTile from '../components/ProfileTile'
import { useApp } from '../store'

const MIN = 1
const MAX = 8

/** Première ouverture : combien êtes-vous, puis qui êtes-vous. */
export default function Setup() {
  const { palette, refresh } = useApp()
  const navigate = useNavigate()

  const [step, setStep] = useState('count')
  const [count, setCount] = useState(2)
  const [people, setPeople] = useState([])
  const [editIndex, setEditIndex] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const toNames = () => {
    setPeople(
      Array.from({ length: count }, (_, index) => ({
        name: '',
        color: palette[(index * 5) % Math.max(1, palette.length)] || '#6366f1',
      })),
    )
    setStep('names')
  }

  const finish = async () => {
    if (people.some((person) => !person.name.trim())) {
      setError('Donne un prénom à chaque tuile.')
      return
    }
    setSaving(true)
    try {
      await api.setup(people)
      await refresh()
      navigate('/profils', { replace: true })
    } catch (setupError) {
      setError(setupError.message)
      setSaving(false)
    }
  }

  return (
    <div className="page page-center">
      <div className="hero">
        <h1>Ménage</h1>
        <p>
          {step === 'count'
            ? 'Combien de personnes vont utiliser l’application ?'
            : 'Donne un prénom et une couleur à chacun.'}
        </p>
      </div>

      {step === 'count' ? (
        <>
          <div className="stepper">
            <button
              type="button"
              onClick={() => setCount((value) => Math.max(MIN, value - 1))}
              disabled={count <= MIN}
              aria-label="Un de moins"
            >
              −
            </button>
            <strong>{count}</strong>
            <button
              type="button"
              onClick={() => setCount((value) => Math.min(MAX, value + 1))}
              disabled={count >= MAX}
              aria-label="Un de plus"
            >
              +
            </button>
          </div>
          <button type="button" className="btn primary block" onClick={toNames}>
            Continuer
          </button>
        </>
      ) : (
        <>
          <div className="grid">
            {people.map((person, index) => (
              <div className="sortable" key={index}>
                <ProfileTile
                  user={{ ...person, name: person.name || `Profil ${index + 1}` }}
                  onSelect={() => setEditIndex(index)}
                  onEdit={() => setEditIndex(index)}
                />
              </div>
            ))}
          </div>

          {error && <p className="form-error center">{error}</p>}

          <div className="stack">
            <button type="button" className="btn primary block" disabled={saving} onClick={finish}>
              {saving ? 'Création…' : 'C’est parti'}
            </button>
            <button type="button" className="btn ghost block" onClick={() => setStep('count')}>
              Revenir en arrière
            </button>
          </div>

          <ProfileForm
            open={editIndex !== null}
            profile={editIndex === null ? null : people[editIndex]}
            palette={palette}
            onClose={() => setEditIndex(null)}
            onSubmit={async (payload) => {
              setPeople((current) =>
                current.map((person, index) => (index === editIndex ? payload : person)),
              )
              setError(null)
            }}
          />
        </>
      )}
    </div>
  )
}
