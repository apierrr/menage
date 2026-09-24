import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from './api'

const AppContext = createContext(null)
export const useApp = () => useContext(AppContext)

const EMPTY = {
  loading: true,
  setup_done: false,
  users: [],
  me: null,
  palette: [],
  settings: {},
  share_window_days: 90,
}

export function AppProvider({ children }) {
  const [state, setState] = useState(EMPTY)
  const [toast, setToast] = useState(null)
  const [ask, setAsk] = useState(null)
  const timer = useRef(null)
  const resolver = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const data = await api.bootstrap()
      setState({ ...EMPTY, ...data, loading: false })
      return data
    } catch (error) {
      setState((prev) => ({ ...prev, loading: false, error: error.message }))
      return null
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  /** Message flottant, avec une action facultative (« Annuler »). */
  const notify = useCallback((message, options = {}) => {
    clearTimeout(timer.current)
    setToast({ message, ...options })
    timer.current = setTimeout(() => setToast(null), options.duration ?? 6000)
  }, [])

  const dismiss = useCallback(() => {
    clearTimeout(timer.current)
    setToast(null)
  }, [])

  /** Confirmation modale ; renvoie une promesse booléenne. */
  const confirm = useCallback(
    (options) =>
      new Promise((resolve) => {
        resolver.current = resolve
        setAsk(options)
      }),
    [],
  )

  const answer = (value) => {
    setAsk(null)
    resolver.current?.(value)
    resolver.current = null
  }

  const value = { ...state, refresh, notify, dismiss, confirm }

  return (
    <AppContext.Provider value={value}>
      {children}
      {toast && (
        <div className="toast" role="status">
          <span className="toast-text">{toast.message}</span>
          {toast.actionLabel && (
            <button
              type="button"
              className="toast-action"
              onClick={() => {
                dismiss()
                toast.onAction?.()
              }}
            >
              {toast.actionLabel}
            </button>
          )}
        </div>
      )}
      {ask && (
        <div className="backdrop" onClick={() => answer(false)}>
          <div className="dialog" onClick={(event) => event.stopPropagation()}>
            <h3>{ask.title}</h3>
            {ask.message && <p>{ask.message}</p>}
            <div className="dialog-actions">
              <button type="button" className="btn ghost" onClick={() => answer(false)}>
                Annuler
              </button>
              <button
                type="button"
                className={`btn ${ask.danger ? 'danger' : 'primary'}`}
                onClick={() => answer(true)}
              >
                {ask.confirmLabel || 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppContext.Provider>
  )
}
