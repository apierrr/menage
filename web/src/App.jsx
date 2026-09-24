import { Navigate, Route, Routes } from 'react-router-dom'
import History from './pages/History'
import Home from './pages/Home'
import ProfilePicker from './pages/ProfilePicker'
import Recap from './pages/Recap'
import Section from './pages/Section'
import Setup from './pages/Setup'
import { useApp } from './store'

/** Aiguillage : installation → choix du profil → application. */
function Gate({ children }) {
  const { loading, setup_done: setupDone, me, error } = useApp()

  if (loading) return <div className="splash">Ménage…</div>
  if (error) return <div className="splash error">{error}</div>
  if (!setupDone) return <Navigate to="/installation" replace />
  if (!me) return <Navigate to="/profils" replace />
  return children
}

function Entry({ children }) {
  const { loading, setup_done: setupDone } = useApp()
  if (loading) return <div className="splash">Ménage…</div>
  if (!setupDone && window.location.pathname !== '/installation')
    return <Navigate to="/installation" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/installation" element={<Setup />} />
      <Route
        path="/profils"
        element={
          <Entry>
            <ProfilePicker />
          </Entry>
        }
      />
      <Route
        path="/"
        element={
          <Gate>
            <Home />
          </Gate>
        }
      />
      <Route
        path="/s/:section"
        element={
          <Gate>
            <Section />
          </Gate>
        }
      />
      <Route
        path="/s/:section/:tileId"
        element={
          <Gate>
            <Section />
          </Gate>
        }
      />
      <Route
        path="/recap"
        element={
          <Gate>
            <Recap />
          </Gate>
        }
      />
      <Route
        path="/historique"
        element={
          <Gate>
            <History />
          </Gate>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
