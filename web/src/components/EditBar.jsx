import { Check, Folder, Plus } from './Icons'

/**
 * Menu flottant du mode édition : créer une tuile, créer un sous-menu, sortir.
 * Il reste collé en bas de l'écran, à portée de pouce.
 */
export default function EditBar({ onAddTask, onAddFolder, onDone, taskLabel = 'Tâche' }) {
  return (
    <div className="editbar">
      <button type="button" className="editbar-btn" onClick={onAddTask}>
        <Plus width={18} height={18} />
        {taskLabel}
      </button>
      {onAddFolder && (
        <button type="button" className="editbar-btn" onClick={onAddFolder}>
          <Folder width={18} height={18} />
          Sous-menu
        </button>
      )}
      <button type="button" className="editbar-btn done" onClick={onDone}>
        <Check width={18} height={18} />
        Terminé
      </button>
    </div>
  )
}
