import { useEffect } from 'react'
import { Cross } from './Icons'

/** Feuille modale qui remonte du bas — le geste attendu sur téléphone. */
export default function Sheet({ open, title, onClose, children, footer }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (event) => event.key === 'Escape' && onClose?.()
    document.body.classList.add('locked')
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.classList.remove('locked')
      window.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="backdrop" onClick={onClose}>
      <div className="sheet" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <div className="sheet-grab" />
        <header className="sheet-head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Fermer">
            <Cross width={18} height={18} />
          </button>
        </header>
        <div className="sheet-body">{children}</div>
        {footer && <div className="sheet-foot">{footer}</div>}
      </div>
    </div>
  )
}
