import { useEffect, useState } from 'react'
import { readableText, splitGradient } from '../colors'
import ColorPicker from './ColorPicker'
import Sheet from './Sheet'

// Mêmes bornes que côté serveur (app/schemas.py).
const MAX_BULLETS = 20
const MAX_BULLET_LENGTH = 200

// Même valeur que côté serveur : rien à refléter, donc rien à colorer.
const NEUTRAL = '#475569'

const PERIODS = [
  { label: 'Tous les jours', kind: 'day', n: 1 },
  { label: '1 semaine', kind: 'week', n: 1 },
  { label: '2 semaines', kind: 'week', n: 2 },
  { label: '3 semaines', kind: 'week', n: 3 },
  { label: '1 mois', kind: 'month', n: 1 },
]

// Une semaine reste le rythme proposé par défaut.
const DEFAULT_PERIOD = PERIODS.findIndex((p) => p.kind === 'week' && p.n === 1)

const ROTATIONS = [
  { value: 'equity', label: 'Équité', hint: 'Revient à qui l’a faite le moins souvent.' },
  { value: 'round_robin', label: 'Chacun son tour', hint: 'Suit l’ordre des profils, sans rattrapage.' },
]

function toISO(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Même règle que le serveur : le jour d'ancrage est écrêté au dernier du mois. */
function addPeriod(from, kind, n) {
  const date = new Date(from)
  if (kind === 'day') {
    date.setDate(date.getDate() + n)
    return date
  }
  if (kind === 'week') {
    date.setDate(date.getDate() + 7 * n)
    return date
  }
  const anchor = date.getDate()
  const lastDay = new Date(date.getFullYear(), date.getMonth() + 1 + n, 0).getDate()
  return new Date(date.getFullYear(), date.getMonth() + n, Math.min(anchor, lastDay))
}

/** Même règle que le serveur : une tâche quotidienne est à faire dès aujourd'hui. */
function firstDue(kind, n) {
  return toISO(kind === 'day' ? new Date() : addPeriod(new Date(), kind, n))
}

export default function TileForm({
  open,
  section,
  kind,
  tile,
  users = [],
  palette = [],
  meId,
  onClose,
  onSubmit,
}) {
  const isEdit = Boolean(tile)
  const effectiveKind = tile?.kind || kind
  // Dans la section régulière, plus rien n'a de couleur choisie : une tâche
  // porte celle de son responsable, un sous-menu celles de ce qu'il contient.
  const isRegularTask = section === 'regular' && effectiveKind === 'task'
  const isRegularFolder = section === 'regular' && effectiveKind === 'folder'

  const [title, setTitle] = useState('')
  const [details, setDetails] = useState('')
  const [color, setColor] = useState(palette[0] || '#3b82f6')
  const [periodIndex, setPeriodIndex] = useState(DEFAULT_PERIOD)
  const [due, setDue] = useState('')
  const [dueTouched, setDueTouched] = useState(false)
  const [assignee, setAssignee] = useState(null)
  const [members, setMembers] = useState([])
  const [rotation, setRotation] = useState('equity')
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setError(null)
    setSaving(false)
    setDueTouched(false)

    if (tile) {
      setTitle(tile.title)
      setDetails((tile.bullets || []).join('\n'))
      setColor(tile.color)
      const found = PERIODS.findIndex(
        (p) => p.kind === tile.regular?.period_kind && p.n === (tile.regular?.period_n || 1),
      )
      setPeriodIndex(found >= 0 ? found : DEFAULT_PERIOD)
      setDue(tile.regular?.due_date || '')
      setAssignee(tile.regular?.assignee?.id ?? null)
      setMembers(tile.members || users.map((user) => user.id))
      setRotation(tile.regular?.rotation_mode || 'equity')
    } else {
      setTitle('')
      setDetails('')
      setColor(palette[Math.floor(Math.random() * Math.max(1, palette.length))] || '#3b82f6')
      setPeriodIndex(DEFAULT_PERIOD)
      setDue(firstDue('week', 1))
      setAssignee(meId ?? users[0]?.id ?? null)
      setMembers(users.map((user) => user.id))
      setRotation('equity')
    }
  }, [open, tile, meId])

  const changePeriod = (index) => {
    setPeriodIndex(index)
    if (!isEdit && !dueTouched) {
      const period = PERIODS[index]
      setDue(firstDue(period.kind, period.n))
    }
  }

  // Au moins une personne reste cochée. Décocher le responsable passe la
  // main à la première personne encore concernée.
  const toggleMember = (userId) => {
    const next = members.includes(userId)
      ? members.filter((id) => id !== userId)
      : [...members, userId]
    if (!next.length) return
    setMembers(next)
    if (!next.includes(assignee)) {
      setAssignee(users.find((user) => next.includes(user.id))?.id ?? null)
    }
  }
  const concerned = users.filter((user) => members.includes(user.id))
  const alone = concerned.length === 1

  const submit = async () => {
    if (!title.trim()) {
      setError('Il faut un titre.')
      return
    }
    const bullets = details
      .split('\n')
      .map((line) => line.replace(/^[-•*]\s*/, '').trim())
      .filter(Boolean)
    if (bullets.length > MAX_BULLETS) {
      setError(`${MAX_BULLETS} puces au maximum (${bullets.length} pour l’instant).`)
      return
    }
    if (bullets.some((line) => line.length > MAX_BULLET_LENGTH)) {
      setError(`Une puce fait ${MAX_BULLET_LENGTH} caractères au maximum.`)
      return
    }
    const period = PERIODS[periodIndex]
    const payload = { title: title.trim(), bullets }
    if (section !== 'regular') payload.color = color
    if (effectiveKind === 'task') payload.member_ids = members

    if (isRegularTask) {
      Object.assign(payload, {
        period_kind: period.kind,
        period_n: period.n,
        rotation_mode: rotation,
        assignee_id: assignee,
        due_date: due || null,
      })
    }

    setSaving(true)
    try {
      await onSubmit(payload)
      onClose()
    } catch (submitError) {
      setError(submitError.message)
      setSaving(false)
    }
  }

  const mix = tile?.folder?.mix || []
  const folderPreview = splitGradient(mix) || NEUTRAL

  const heading = isEdit
    ? 'Modifier la tuile'
    : effectiveKind === 'folder'
      ? 'Nouveau sous-menu'
      : section === 'regular'
        ? 'Nouvelle tâche régulière'
        : 'Nouvelle tâche ponctuelle'

  return (
    <Sheet
      open={open}
      title={heading}
      onClose={onClose}
      footer={
        <>
          {error && <p className="form-error">{error}</p>}
          <button type="button" className="btn primary block" disabled={saving} onClick={submit}>
            {saving ? 'Enregistrement…' : isEdit ? 'Enregistrer' : 'Créer'}
          </button>
        </>
      }
    >
      <label className="field">
        <span>Titre</span>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={effectiveKind === 'folder' ? 'Salle de bain' : 'Nettoyer la douche'}
          maxLength={120}
          autoFocus={!isEdit}
        />
      </label>

      {effectiveKind === 'task' && (
        <label className="field">
          <span>Détails (une puce par ligne, {MAX_BULLETS} au maximum)</span>
          <textarea
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            rows={3}
            placeholder={'sol\nmiroir\nlavabo'}
          />
        </label>
      )}

      {effectiveKind === 'task' && users.length > 1 && (
        <div className="field">
          <span>Personnes concernées</span>
          <div className="segmented wrap">
            {users.map((user) => {
              const on = members.includes(user.id)
              return (
                <button
                  type="button"
                  key={user.id}
                  className={on ? 'on' : ''}
                  style={on ? { background: user.color, color: readableText(user.color) } : undefined}
                  onClick={() => toggleMember(user.id)}
                >
                  {!on && <i className="dot" style={{ background: user.color }} />}
                  {user.name}
                </button>
              )
            })}
          </div>
          <p className="hint">
            {concerned.length === users.length
              ? 'Tout le monde, y compris les profils ajoutés plus tard.'
              : isRegularTask
                ? alone
                  ? `Toujours pour ${concerned[0].name}.`
                  : 'La tâche ne tourne qu’entre ces personnes.'
                : 'La jauge ne compare que ces personnes.'}
          </p>
        </div>
      )}

      {isRegularTask && (
        <>
          <div className="field">
            <span>Régularité</span>
            <div className="segmented">
              {PERIODS.map((period, index) => (
                <button
                  type="button"
                  key={period.label}
                  className={index === periodIndex ? 'on' : ''}
                  onClick={() => changePeriod(index)}
                >
                  {period.label}
                </button>
              ))}
            </div>
            {PERIODS[periodIndex].kind === 'month' && (
              <p className="hint">
                Calé sur le jour du mois : un 31 retombe au 28 ou 29 en février, puis revient au 31.
              </p>
            )}
          </div>

          <label className="field">
            <span>{isEdit ? 'Prochaine échéance' : 'Première échéance'}</span>
            <input
              type="date"
              value={due}
              onChange={(event) => {
                setDue(event.target.value)
                setDueTouched(true)
              }}
            />
          </label>

          {!alone && (
            <div className="field">
              <span>{isEdit ? 'Qui doit la faire' : 'Qui commence'}</span>
              <div className="segmented wrap">
                {concerned.map((user) => (
                  <button
                    type="button"
                    key={user.id}
                    className={assignee === user.id ? 'on' : ''}
                    // La sélection prend la couleur de la personne : c'est elle
                    // que portera la tuile.
                    style={
                      assignee === user.id
                        ? { background: user.color, color: readableText(user.color) }
                        : undefined
                    }
                    onClick={() => setAssignee(user.id)}
                  >
                    {assignee !== user.id && <i className="dot" style={{ background: user.color }} />}
                    {user.name}
                  </button>
                ))}
              </div>
            </div>

          )}

          {!alone && (
            <div className="field">
              <span>Rotation ensuite</span>
              <div className="segmented">
                {ROTATIONS.map((mode) => (
                  <button
                    type="button"
                    key={mode.value}
                    className={rotation === mode.value ? 'on' : ''}
                    onClick={() => setRotation(mode.value)}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
              <p className="hint">{ROTATIONS.find((mode) => mode.value === rotation)?.hint}</p>
            </div>
          )}
        </>
      )}

      <div className="field">
        <span>Couleur</span>
        {isRegularTask && (
          <div className="color-follow">
            <span
              className="picker-preview"
              style={{ background: users.find((user) => user.id === assignee)?.color || NEUTRAL }}
            />
            <p className="hint">
              Elle suit la personne qui doit faire la tâche
              {users.find((user) => user.id === assignee)?.name
                ? ` — ${users.find((user) => user.id === assignee).name} pour l’instant`
                : ''}
              , et change avec la rotation.
            </p>
          </div>
        )}

        {isRegularFolder && (
          <div className="color-follow">
            <span className="picker-preview" style={{ background: folderPreview }} />
            <p className="hint">
              {mix.length
                ? `Elle se partage entre les responsables des tâches du dessous : ${mix
                    .map((part) => `${part.name} ${part.count}`)
                    .join(', ')}.`
                : 'Elle se partagera entre les responsables des tâches que ce sous-menu contiendra, au prorata.'}
            </p>
          </div>
        )}

        {!isRegularTask && !isRegularFolder && (
          <ColorPicker value={color} onChange={setColor} palette={palette} />
        )}
      </div>
    </Sheet>
  )
}
