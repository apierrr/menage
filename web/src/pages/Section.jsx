import { useCallback, useEffect, useState } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import EditBar from '../components/EditBar'
import TileForm from '../components/TileForm'
import TileGrid from '../components/TileGrid'
import TopBar from '../components/TopBar'
import { useApp } from '../store'

const LABELS = { regular: 'Régulière', oneoff: 'Ponctuelle' }
const SORT_KEY = 'menage.sort'

export default function Section() {
  const { section, tileId } = useParams()
  const parentId = tileId ? Number(tileId) : null
  const { users, me, palette, notify, confirm } = useApp()
  const navigate = useNavigate()

  const [data, setData] = useState(null)
  const [editing, setEditing] = useState(false)
  const [busyId, setBusyId] = useState(null)
  const [form, setForm] = useState(null)
  const [failure, setFailure] = useState(null)
  const [sort, setSort] = useState(() => localStorage.getItem(SORT_KEY) || 'auto')

  const load = useCallback(async () => {
    try {
      setData(await api.tiles(section, parentId, sort))
      setFailure(null)
    } catch (error) {
      setFailure(error.message)
    }
  }, [section, parentId, sort])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setEditing(false)
  }, [parentId, section])

  if (!LABELS[section]) return <Navigate to="/" replace />

  const tiles = data?.tiles || []
  const trail = data?.breadcrumb || []
  const isRegular = section === 'regular'
  const manual = sort === 'manual'

  const goUp = () => {
    if (trail.length > 1) navigate(`/s/${section}/${trail[trail.length - 2].id}`)
    else if (trail.length === 1) navigate(`/s/${section}`)
    else navigate('/')
  }

  /** Un dossier s'ouvre, une tâche se valide — d'un seul appui. */
  const open = async (tile) => {
    if (tile.kind === 'folder') {
      navigate(`/s/${section}/${tile.id}`)
      return
    }
    setBusyId(tile.id)
    try {
      const result = await api.complete(tile.id)
      await load()
      // Rappuyer sur une tâche déjà faite aujourd'hui ne compte pas une
      // deuxième fois ; « Annuler » vise alors la validation d'origine.
      const message = result.repeat
        ? `${tile.title} : déjà validé aujourd'hui`
        : `${tile.title} : c'est validé`
      notify(message, {
        actionLabel: 'Annuler',
        duration: 8000,
        onAction: async () => {
          try {
            await api.undo(result.completion_id)
            await load()
          } catch (error) {
            notify(error.message)
          }
        },
      })
    } catch (error) {
      notify(error.message)
    } finally {
      setBusyId(null)
    }
  }

  const remove = async (tile) => {
    const count = tile.folder?.task_count ?? 0
    const ok = await confirm({
      title: `Supprimer « ${tile.title} » ?`,
      message:
        tile.kind === 'folder' && count > 0
          ? `Ce sous-menu contient ${count} tâche${count > 1 ? 's' : ''} : tout sera supprimé.`
          : 'Son historique de validations sera effacé aussi.',
      confirmLabel: 'Supprimer',
      danger: true,
    })
    if (!ok) return
    try {
      await api.deleteTile(tile.id)
      await load()
    } catch (error) {
      notify(error.message)
    }
  }

  const reorder = async (ids) => {
    const byId = new Map(tiles.map((tile) => [tile.id, tile]))
    setData((current) => ({ ...current, tiles: ids.map((id) => byId.get(id)) }))
    try {
      await api.reorder(section, parentId, ids)
      if (isRegular && !manual) await load()
    } catch (error) {
      notify(error.message)
      load()
    }
  }

  const changeSort = (value) => {
    localStorage.setItem(SORT_KEY, value)
    setSort(value)
  }

  const submitForm = async (payload) => {
    if (form?.tile) await api.updateTile(form.tile.id, payload)
    else
      await api.createTile({
        ...payload,
        section,
        parent_id: parentId,
        kind: form.kind,
      })
    await load()
  }

  return (
    <div className="page">
      <TopBar
        title={data?.parent?.title || LABELS[section]}
        me={me}
        editing={editing}
        onToggleEdit={() => setEditing((value) => !value)}
        back={{
          label: trail.length > 1 ? trail[trail.length - 2].title : trail.length === 1 ? LABELS[section] : 'Accueil',
          onClick: goUp,
        }}
      />

      {isRegular && tiles.length > 0 && (
        <div className="sortbar">
          <span>Ordre</span>
          <div className="segmented tiny">
            <button type="button" className={manual ? '' : 'on'} onClick={() => changeSort('auto')}>
              Urgence
            </button>
            <button type="button" className={manual ? 'on' : ''} onClick={() => changeSort('manual')}>
              Le mien
            </button>
          </div>
        </div>
      )}

      {editing && (
        <p className="hint edit-hint">
          Appui maintenu sur une tuile pour la déplacer.
          {isRegular && !manual && tiles.length > 1 && (
            <> L’ordre affiché suit l’urgence : passe sur « Le mien » pour que ton classement tienne.</>
          )}
        </p>
      )}

      {failure && <p className="form-error center">{failure}</p>}

      {tiles.length === 0 && !failure && (
        <div className="empty">
          <p>
            {parentId ? 'Ce sous-menu est vide.' : `Aucune tâche ${isRegular ? 'régulière' : 'ponctuelle'} pour l’instant.`}
          </p>
          <button
            type="button"
            className="btn primary"
            onClick={() => {
              setEditing(true)
              setForm({ kind: 'task' })
            }}
          >
            Créer la première tuile
          </button>
        </div>
      )}

      <TileGrid
        tiles={tiles}
        users={users}
        meId={me?.id}
        editing={editing}
        busyId={busyId}
        onOpen={open}
        onEdit={(tile) => setForm({ tile })}
        onDelete={remove}
        onReorder={reorder}
      />

      {editing && (
        <EditBar
          onAddTask={() => setForm({ kind: 'task' })}
          onAddFolder={() => setForm({ kind: 'folder' })}
          onDone={() => setEditing(false)}
        />
      )}

      <TileForm
        open={Boolean(form)}
        section={section}
        kind={form?.kind}
        tile={form?.tile}
        users={users}
        palette={palette}
        meId={me?.id}
        onClose={() => setForm(null)}
        onSubmit={submitForm}
      />
    </div>
  )
}
