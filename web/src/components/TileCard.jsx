import { MINE, OTHERS, OVERDUE, readableText, splitGradient } from '../colors'
import { Check, Chevron, Cross, Folder as FolderIcon, Pencil } from './Icons'

/** Décompte en jours pleins : positif = il reste du temps, négatif = retard. */
function counter(days) {
  if (days === null || days === undefined) return null
  if (days === 0) return { value: 0, caption: "aujourd'hui" }
  if (days > 0) return { value: days, caption: 'restants' }
  return { value: -days, caption: 'en retard' }
}

function segments(share, users, meId) {
  const byId = new Map((share?.shares || []).map((entry) => [entry.user_id, entry]))
  let greyIndex = 0
  return users.map((user) => {
    const entry = byId.get(user.id) || { count: 0, pct: 0 }
    const isMe = user.id === meId
    return {
      user,
      isMe,
      count: entry.count,
      pct: entry.pct,
      color: isMe ? MINE : OTHERS[greyIndex++ % OTHERS.length],
    }
  })
}

/**
 * Indicateur d'équité d'une tâche ponctuelle.
 *
 * On affiche des *nombres de fois*, pas des pourcentages : à 3 contre 2, un
 * « 60 % / 40 % » fait paraître énorme un écart d'une seule fois. Le repère
 * blanc sur la barre marque le partage égal (50 % à deux, 33 % à trois…) :
 * si le vert le dépasse, tu en fais plus que ta part.
 */
function ShareIndicator({ share, users, meId }) {
  const ordered = segments(share, users, meId)
  const mine = ordered.find((part) => part.isMe)
  const others = ordered.filter((part) => !part.isMe)
  // Ma part toujours à gauche, sinon la comparaison avec le repère ne veut rien dire.
  const parts = mine ? [mine, ...others] : ordered
  const total = share?.total || 0
  const fairShare = users.length > 1 ? 100 / users.length : null

  let verdict = null
  // Pas concerné par la tâche : rien à comparer, juste le total.
  if (total > 0 && mine && others.length > 0) {
    const othersAverage = others.reduce((sum, part) => sum + part.count, 0) / others.length
    const gap = Math.round((mine?.count ?? 0) - othersAverage)
    verdict = gap === 0 ? 'à l’équilibre' : gap > 0 ? `${gap} de plus` : `${-gap} de moins`
  } else if (total > 0) {
    verdict = `${total} fois`
  }

  return (
    // Classes en `tally-*` et non `share-*` : les bloqueurs de publicité
    // masquent `.share-bar` et `.share-legend` (voir styles.css).
    <div className="tally">
      <div className="tally-track">
        {parts
          .filter((part) => part.count > 0)
          .map((part) => (
            <span
              key={part.user.id}
              style={{ flexGrow: part.count, background: part.color }}
              title={`${part.user.name} — ${part.count}`}
            />
          ))}
        {fairShare !== null && total > 0 && (
          <span className="tally-mark" style={{ left: `${fairShare}%` }} />
        )}
      </div>

      <div className="tally-keys">
        {total === 0 ? (
          <span className="muted-on-tile">jamais fait</span>
        ) : (
          parts
            .filter((part) => part.count > 0)
            .map((part) => (
              <span key={part.user.id} className="tally-key">
                <i style={{ background: part.color }} />
                {part.count}
              </span>
            ))
        )}
        {verdict && <span className="tally-verdict">{verdict}</span>}
      </div>
    </div>
  )
}

export default function TileCard({
  tile,
  users = [],
  meId = null,
  editing = false,
  showPencil = false,
  wide = false,
  busy = false,
  subtitle = null,
  onOpen,
  onEdit,
  onDelete,
}) {
  const regular = tile.regular
  const folder = tile.folder
  const overdue = Boolean(regular?.is_overdue || folder?.is_overdue)
  const background = overdue ? OVERDUE : tile.color
  const isFolder = tile.kind === 'folder'
  const days = counter(regular ? regular.days_left : folder?.days_left)
  const oneoff = tile.oneoff || (isFolder && folder?.shares ? folder : null)
  // Une tuile en retard passe au rouge et perd donc la couleur de son
  // responsable : un liseré la rappelle sur le bord.
  const assigneeColor = regular?.assignee?.color

  // Un sous-menu régulier n'a pas de couleur à lui : il porte, en bandes
  // proportionnelles, celles des personnes qui doivent faire les tâches qu'il
  // contient. Le rouge du retard reste prioritaire, c'est plus urgent à voir.
  const mix = !overdue && folder?.mix?.length ? folder.mix : null
  const split = mix ? splitGradient(mix) : null
  const foreground = readableText(background)
  // Bandes claires et sombres à la fois : sans halo, le titre disparaît sur
  // l'une ou sur l'autre.
  const shaded = mix ? new Set(mix.map((part) => readableText(part.color))).size > 1 : false

  return (
    <article
      className={[
        'tile',
        wide ? 'tile-wide' : '',
        overdue ? 'tile-overdue' : '',
        overdue && assigneeColor ? 'tile-who' : '',
        split ? 'tile-split' : '',
        shaded ? 'tile-shaded' : '',
        editing ? 'tile-editing' : '',
        busy ? 'tile-busy' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={{
        '--bg': background,
        '--fg': foreground,
        '--who': assigneeColor || 'transparent',
        '--split': split || undefined,
        '--halo': foreground === '#ffffff' ? 'rgba(0, 0, 0, 0.55)' : 'rgba(255, 255, 255, 0.6)',
      }}
    >
      {/* En mode édition la surface laisse passer les événements (CSS
          pointer-events) pour que le glisser-déposer parte de n'importe où
          sur la tuile — un bouton `disabled` les avalerait. */}
      <button
        type="button"
        className="tile-surface"
        disabled={busy}
        onClick={editing ? undefined : onOpen}
        tabIndex={editing ? -1 : 0}
        // Les bandes de couleur ne disent rien à voix haute : on énonce la
        // répartition qu'elles représentent.
        aria-label={
          mix
            ? `${tile.title} — ${mix.map((part) => `${part.name} ${part.count}`).join(', ')}`
            : tile.title
        }
      >
        <header className="tile-head">
          <h3 className="tile-title">{tile.title}</h3>
          {isFolder && <FolderIcon className="tile-folder-icon" width={16} height={16} />}
        </header>

        {tile.bullets?.length > 0 && (
          <ul className="bullets">
            {tile.bullets.slice(0, 4).map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        )}

        {subtitle && <p className="tile-subtitle">{subtitle}</p>}

        {oneoff && (
          <ShareIndicator
            share={oneoff}
            // Une tâche réservée à certaines personnes ne compare qu'elles.
            users={tile.members ? users.filter((user) => tile.members.includes(user.id)) : users}
            meId={meId}
          />
        )}

        {/* Une tâche ponctuelle n'a rien à mettre en pied : son indicateur
            occupe déjà le bas de la tuile. */}
        {(isFolder || days) && (
          <footer className="tile-foot">
            <div className="tile-foot-left">
              {isFolder && (
                <span className="chip">
                  {folder?.task_count ?? 0} {folder?.task_count > 1 ? 'tâches' : 'tâche'}
                </span>
              )}
              {/* Déjà faite aujourd'hui : évite le second appui inutile. */}
              {regular?.done_today && (
                <span className="chip">
                  <Check width={12} height={12} />
                  faite
                </span>
              )}
            </div>

            {days && (
              <div className="counter">
                <strong>
                  {days.value}
                  <span>j</span>
                </strong>
                <small>{days.caption}</small>
              </div>
            )}
            {isFolder && !days && <Chevron className="tile-chevron" width={18} height={18} />}
          </footer>
        )}
      </button>

      {editing && onDelete && (
        <button
          type="button"
          className="tile-remove"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={onDelete}
          aria-label={`Supprimer ${tile.title}`}
        >
          <Cross width={16} height={16} />
        </button>
      )}

      {(editing || showPencil) && onEdit && (
        <button
          type="button"
          className="tile-edit"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={onEdit}
          aria-label={`Modifier ${tile.title}`}
        >
          <Pencil width={15} height={15} />
        </button>
      )}
    </article>
  )
}
