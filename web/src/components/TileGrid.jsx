import { DndContext, MouseSensor, TouchSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, arrayMove, rectSortingStrategy, useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import TileCard from './TileCard'

/**
 * La grille : deux tuiles par étage, sauf `wide` (l'accueil) où chaque tuile
 * occupe la largeur entière. En mode édition, les tuiles deviennent
 * déplaçables au doigt pour changer leur ordre.
 */
function Sortable({ id, children }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })

  return (
    <div
      ref={setNodeRef}
      className={`sortable sortable-live ${isDragging ? 'is-dragging' : ''}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 20 : undefined,
      }}
      {...attributes}
      {...listeners}
    >
      {children}
    </div>
  )
}

export default function TileGrid({
  tiles,
  users,
  meId,
  editing = false,
  wide = false,
  busyId = null,
  subtitleFor,
  onOpen,
  onEdit,
  onDelete,
  onReorder,
}) {
  // Capteurs séparés souris / tactile, et surtout PAS de PointerSensor : sur
  // téléphone il ne peut pas empêcher le navigateur de partir en défilement,
  // le geste était donc perdu. Le TouchSensor écoute les événements tactiles
  // en non-passif et bloque le défilement une fois l'appui maintenu validé.
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } }),
  )

  const ids = tiles.map((tile) => tile.id)
  const className = `grid ${wide ? 'grid-wide' : ''}`

  const card = (tile) => (
    <TileCard
      tile={tile}
      users={users}
      meId={meId}
      editing={editing}
      wide={wide}
      busy={busyId === tile.id}
      subtitle={subtitleFor ? subtitleFor(tile) : null}
      onOpen={() => onOpen?.(tile)}
      onEdit={onEdit ? () => onEdit(tile) : undefined}
      onDelete={onDelete ? () => onDelete(tile) : undefined}
    />
  )

  if (!editing || !onReorder) {
    return (
      <div className={className}>
        {tiles.map((tile) => (
          <div className="sortable" key={tile.id}>
            {card(tile)}
          </div>
        ))}
      </div>
    )
  }

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return
    const from = ids.indexOf(active.id)
    const to = ids.indexOf(over.id)
    if (from < 0 || to < 0) return
    onReorder(arrayMove(ids, from, to))
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div className={className}>
          {tiles.map((tile) => (
            <Sortable id={tile.id} key={tile.id}>
              {card(tile)}
            </Sortable>
          ))}
        </div>
      </SortableContext>
    </DndContext>
  )
}
