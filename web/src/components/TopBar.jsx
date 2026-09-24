import { useNavigate } from 'react-router-dom'
import { readableText } from '../colors'
import { Back, Brush } from './Icons'

function Avatar({ user, onClick }) {
  const color = user?.color || '#475569'
  return (
    <button
      type="button"
      className="avatar"
      style={{ background: color, color: readableText(color) }}
      onClick={onClick}
      aria-label="Récapitulatif et changement de profil"
    >
      {(user?.name || '?').trim().charAt(0).toUpperCase()}
    </button>
  )
}

/**
 * Bandeau commun aux menus : le sigle de l'utilisateur à gauche (il ouvre le
 * récap), le pinceau à droite (il fait basculer la page en mode édition).
 */
export default function TopBar({ title, me, editing, onToggleEdit, back }) {
  const navigate = useNavigate()

  return (
    <header className="topbar">
      <div className="topbar-row">
        <Avatar user={me} onClick={() => navigate('/recap')} />
        <h1 className="topbar-title">{title}</h1>
        {onToggleEdit ? (
          <button
            type="button"
            className={`icon-btn ${editing ? 'on' : ''}`}
            onClick={onToggleEdit}
            aria-label={editing ? 'Quitter le mode édition' : 'Modifier les tuiles'}
            aria-pressed={editing}
          >
            <Brush />
          </button>
        ) : (
          <span className="icon-btn ghosted" aria-hidden="true" />
        )}
      </div>

      {back && (
        <button type="button" className="crumb" onClick={back.onClick}>
          <Back width={16} height={16} />
          {back.label}
        </button>
      )}
    </header>
  )
}
