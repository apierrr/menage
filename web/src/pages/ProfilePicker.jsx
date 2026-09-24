import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import EditBar from '../components/EditBar'
import { Brush } from '../components/Icons'
import ProfileForm from '../components/ProfileForm'
import ProfileTile from '../components/ProfileTile'
import { useApp } from '../store'

/** Choix du profil. L'identité est ensuite gardée dans un cookie d'un an. */
export default function ProfilePicker() {
  const { users, me, palette, refresh, confirm, notify } = useApp()
  const navigate = useNavigate()

  const [editing, setEditing] = useState(false)
  const [target, setTarget] = useState(null) // profil en cours de réglage
  const [creating, setCreating] = useState(false)

  const choose = async (user) => {
    await api.openSession(user.id)
    await refresh()
    navigate('/', { replace: true })
  }

  const remove = async (user) => {
    const ok = await confirm({
      title: `Supprimer ${user.name} ?`,
      message: 'Ses validations passées seront effacées et les tâches qui lui étaient attribuées seront redistribuées.',
      confirmLabel: 'Supprimer',
      danger: true,
    })
    if (!ok) return
    try {
      await api.deleteUser(user.id)
      await refresh()
    } catch (error) {
      notify(error.message)
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-row">
          <span className="icon-btn ghosted" aria-hidden="true" />
          <h1 className="topbar-title">Qui es-tu ?</h1>
          <button
            type="button"
            className={`icon-btn ${editing ? 'on' : ''}`}
            onClick={() => setEditing((value) => !value)}
            aria-label="Modifier les profils"
            aria-pressed={editing}
          >
            <Brush />
          </button>
        </div>
      </header>

      <div className="grid">
        {users.map((user) => (
          <div className="sortable" key={user.id}>
            <ProfileTile
              user={user}
              selected={me?.id === user.id}
              showPencil={editing}
              onSelect={editing ? undefined : () => choose(user)}
              onEdit={editing ? () => setTarget(user) : undefined}
              onDelete={editing && users.length > 1 ? () => remove(user) : undefined}
            />
          </div>
        ))}
      </div>

      {editing && (
        <EditBar
          taskLabel="Profil"
          onAddTask={() => setCreating(true)}
          onDone={() => setEditing(false)}
        />
      )}

      <ProfileForm
        open={Boolean(target) || creating}
        profile={target}
        palette={palette}
        onClose={() => {
          setTarget(null)
          setCreating(false)
        }}
        onSubmit={async (payload) => {
          if (target) await api.updateUser(target.id, payload)
          else await api.createUser(payload)
          await refresh()
        }}
      />
    </div>
  )
}
