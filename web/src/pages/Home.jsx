import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import ColorPicker from '../components/ColorPicker'
import Sheet from '../components/Sheet'
import TileCard from '../components/TileCard'
import TopBar from '../components/TopBar'
import { useApp } from '../store'

/**
 * Accueil : deux tuiles, chacune sur toute la largeur. C'est la seule page qui
 * n'applique pas la grille à deux colonnes.
 */
export default function Home() {
  const { me, palette, settings, refresh } = useApp()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [editing, setEditing] = useState(false)
  const [tuning, setTuning] = useState(null)

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [])

  const mine = stats?.users?.find((user) => user.is_me)
  const overdue = stats?.global?.overdue ?? 0

  const sections = [
    {
      id: 'regular',
      key: 'home_regular',
      section: 'regular',
      kind: 'folder',
      title: 'Régulière',
      color: settings?.home_regular || '#4f46e5',
      bullets: [],
      folder: { task_count: stats?.global?.regular_tasks ?? 0 },
      subtitle: stats
        ? [
            `${mine?.assigned ?? 0} pour toi`,
            overdue > 0 ? `${overdue} en retard` : 'rien en retard',
          ].join(' · ')
        : null,
    },
    {
      id: 'oneoff',
      key: 'home_oneoff',
      section: 'oneoff',
      kind: 'folder',
      title: 'Ponctuelle',
      color: settings?.home_oneoff || '#0d9488',
      bullets: [],
      folder: { task_count: stats?.global?.oneoff_tasks ?? 0 },
      subtitle: stats
        ? `${stats.global.oneoff_done} validations sur ${stats.window_days} jours`
        : null,
    },
  ]

  return (
    <div className="page">
      <TopBar
        title="Ménage"
        me={me}
        editing={editing}
        onToggleEdit={() => setEditing((value) => !value)}
      />

      <div className="grid grid-wide">
        {sections.map((tile) => (
          <div className="sortable" key={tile.id}>
            <TileCard
              tile={tile}
              wide
              editing={editing}
              subtitle={tile.subtitle}
              onOpen={() => navigate(`/s/${tile.section}`)}
              onEdit={() => setTuning(tile)}
            />
          </div>
        ))}
      </div>

      {editing && (
        <p className="hint center">
          Ces deux tuiles sont fixes : seule leur couleur se modifie.
          <br />
          <button type="button" className="btn ghost" onClick={() => setEditing(false)}>
            Terminé
          </button>
        </p>
      )}

      <Sheet open={Boolean(tuning)} title={`Couleur — ${tuning?.title}`} onClose={() => setTuning(null)}>
        <ColorPicker
          value={tuning?.color}
          palette={palette}
          onChange={async (color) => {
            setTuning((current) => ({ ...current, color }))
            await api.updateSettings({ [tuning.key]: color })
            await refresh()
          }}
        />
      </Sheet>
    </div>
  )
}
