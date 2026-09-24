import { readableText } from '../colors'
import { Cross, Pencil } from './Icons'

/** Tuile de profil : même matière que les autres, contenu différent. */
export default function ProfileTile({
  user,
  selected = false,
  showPencil = true,
  onSelect,
  onEdit,
  onDelete,
}) {
  const color = user.color || '#475569'

  return (
    <article
      className={`tile tile-profile ${selected ? 'tile-selected' : ''}`}
      style={{ '--bg': color, '--fg': readableText(color) }}
    >
      <button type="button" className="tile-surface" onClick={onSelect} disabled={!onSelect}>
        <span className="profile-initial">{(user.name || '?').trim().charAt(0).toUpperCase()}</span>
        <h3 className="tile-title profile-name">{user.name || 'Sans nom'}</h3>
      </button>

      {onDelete && (
        <button
          type="button"
          className="tile-remove"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={onDelete}
          aria-label={`Supprimer ${user.name}`}
        >
          <Cross width={16} height={16} />
        </button>
      )}

      {showPencil && onEdit && (
        <button
          type="button"
          className="tile-edit"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={onEdit}
          aria-label={`Modifier ${user.name}`}
        >
          <Pencil width={15} height={15} />
        </button>
      )}
    </article>
  )
}
