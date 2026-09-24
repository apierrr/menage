import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { Cross } from '../components/Icons'
import TopBar from '../components/TopBar'
import { useApp } from '../store'

const DAY = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })
const TIME = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' })

const toISO = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

/** Titre d'un groupe : aujourd'hui, hier, puis la date en toutes lettres. */
function dayLabel(iso) {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (iso === toISO(today)) return "Aujourd'hui"
  if (iso === toISO(yesterday)) return 'Hier'
  return DAY.format(new Date(`${iso}T12:00:00`))
}

/** Journal des validations : relire ce qui a été coché, et le corriger. */
export default function History() {
  const { me, confirm, notify } = useApp()
  const navigate = useNavigate()
  const [entries, setEntries] = useState(null)
  const [busy, setBusy] = useState(null)

  const load = useCallback(async () => {
    try {
      const data = await api.history()
      setEntries(data.entries)
    } catch (error) {
      notify(error.message)
    }
  }, [notify])

  useEffect(() => {
    load()
  }, [load])

  const remove = async (entry) => {
    const ok = await confirm({
      title: `Supprimer cette validation ?`,
      message: entry.is_last
        ? `« ${entry.tile_title} » repassera à l’échéance et au responsable d’avant.`
        : `Elle disparaîtra des compteurs de « ${entry.tile_title} ». L’échéance en cours, elle, ne sera pas recalculée.`,
      confirmLabel: 'Supprimer',
      danger: true,
    })
    if (!ok) return
    setBusy(entry.id)
    try {
      await api.undo(entry.id)
      await load()
    } catch (error) {
      notify(error.message)
    } finally {
      setBusy(null)
    }
  }

  // Regroupement par jour, l'ordre du serveur étant déjà du plus récent au plus ancien.
  const groups = []
  for (const entry of entries || []) {
    if (!groups.length || groups[groups.length - 1].day !== entry.on) {
      groups.push({ day: entry.on, items: [] })
    }
    groups[groups.length - 1].items.push(entry)
  }

  return (
    <div className="page">
      <TopBar
        title="Historique"
        me={me}
        back={{ label: 'Récapitulatif', onClick: () => navigate('/recap') }}
      />

      {entries === null && <p className="hint center">Chargement…</p>}

      {entries?.length === 0 && (
        <div className="empty">
          <p>Aucune validation pour le moment.</p>
        </div>
      )}

      {groups.map((group) => (
        <section key={group.day} className="log-group">
          <h2 className="panel-title">{dayLabel(group.day)}</h2>
          <ul className="log">
            {group.items.map((entry) => (
              <li key={entry.id} className={busy === entry.id ? 'log-row busy' : 'log-row'}>
                <span className="dot" style={{ background: entry.user.color }} />
                <div className="log-body">
                  <strong>{entry.tile_title}</strong>
                  <span className="log-meta">
                    {entry.user.name} · {TIME.format(new Date(entry.at))}
                    {entry.section === 'regular' && !entry.is_last && ' · validation ancienne'}
                    {entry.was_late && ` · ${entry.days_late} j de retard`}
                  </span>
                </div>
                <button
                  type="button"
                  className="log-remove"
                  onClick={() => remove(entry)}
                  disabled={busy === entry.id}
                  aria-label={`Supprimer la validation de ${entry.tile_title}`}
                >
                  <Cross width={16} height={16} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
