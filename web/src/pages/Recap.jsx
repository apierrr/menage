import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import TopBar from '../components/TopBar'
import { useApp } from '../store'

function Metric({ value, label, alert = false }) {
  return (
    <div className={`metric ${alert ? 'metric-alert' : ''}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
}

/** Vue d'ensemble : les indicateurs globaux, puis chacun en détail. */
export default function Recap() {
  const { me, refresh, notify } = useApp()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch((error) => notify(error.message))
  }, [notify])

  const switchUser = async () => {
    await api.closeSession()
    await refresh()
    navigate('/profils', { replace: true })
  }

  const total = stats?.global?.done || 0

  return (
    <div className="page">
      {/*
        Destination fixe, pas `navigate(-1)` : le récap s'atteint depuis
        n'importe où (le sigle du bandeau), et l'historique — qui n'est
        accessible que d'ici — remonte vers le récap. Un retour en arrière
        renvoyait donc à l'historique, dont le fil d'Ariane ramenait au récap :
        les deux pages se renvoyaient l'une à l'autre sans jamais sortir.
        Le fil d'Ariane remonte d'un cran dans `/` → `/recap` → `/historique`,
        comme celui des sections remonte dans leur arborescence.
      */}
      <TopBar
        title="Récapitulatif"
        me={me}
        back={{ label: 'Accueil', onClick: () => navigate('/') }}
      />

      {!stats ? (
        <p className="hint center">Chargement…</p>
      ) : (
        <>
          <section className="panel">
            <div className="metrics">
              <Metric value={stats.global.overdue} label="en retard" alert={stats.global.overdue > 0} />
              <Metric value={stats.global.regular_tasks} label="tâches régulières" />
              <Metric value={stats.global.oneoff_tasks} label="tâches ponctuelles" />
              <Metric value={stats.global.done} label={`validations (${stats.window_days} j)`} />
            </div>

            <h2 className="panel-title">Répartition générale</h2>
            <div className="tally-track big">
              {total === 0 ? (
                <span className="tally-void" />
              ) : (
                stats.users
                  .filter((user) => user.done > 0)
                  .map((user) => (
                    <span
                      key={user.id}
                      style={{ flexGrow: user.done, background: user.color }}
                      title={`${user.name} — ${user.done}`}
                    />
                  ))
              )}
            </div>
            <div className="tally-keys spread">
              {stats.users.map((user) => (
                <span key={user.id} className="tally-key">
                  <i style={{ background: user.color }} />
                  {user.name} {Math.round(user.share_pct)}&nbsp;%
                </span>
              ))}
            </div>
          </section>

          {stats.users.map((user) => (
            <section className={`panel user-panel ${user.is_me ? 'is-me' : ''}`} key={user.id}>
              <header className="user-head">
                <span className="dot big" style={{ background: user.color }} />
                <h2>
                  {user.name}
                  {user.is_me && <em> — toi</em>}
                </h2>
              </header>
              <div className="metrics">
                <Metric value={user.done} label={`validations (${stats.window_days} j)`} />
                <Metric value={`${Math.round(user.share_pct)} %`} label="de la charge" />
                <Metric value={user.assigned} label="tâches à venir" />
                <Metric value={user.overdue} label="en retard" alert={user.overdue > 0} />
              </div>
              <p className="hint">
                {user.next_days_left === null
                  ? 'Aucune échéance en attente.'
                  : user.next_days_left < 0
                    ? `Prochaine tâche en retard de ${-user.next_days_left} jour${-user.next_days_left > 1 ? 's' : ''}.`
                    : `Prochaine tâche dans ${user.next_days_left} jour${user.next_days_left > 1 ? 's' : ''}.`}
                {user.late_done > 0 && ` ${user.late_done} validation${user.late_done > 1 ? 's' : ''} hors délai.`}
              </p>
            </section>
          ))}

          <div className="stack spaced">
            <button
              type="button"
              className="btn block"
              onClick={() => navigate('/historique')}
            >
              Historique des actions
            </button>
            <button type="button" className="btn ghost block" onClick={switchUser}>
              Changer d’utilisateur
            </button>
          </div>
        </>
      )}
    </div>
  )
}
