import { Route, Routes } from 'react-router'
import MenuPrincipal from './components/MenuPrincipal.jsx'
import Inicio from './pages/Inicio.jsx'
import PerfilProspeccao from './pages/PerfilProspeccao.jsx'
import Resultados from './pages/Resultados.jsx'

export default function App() {
  return (
    <div className="flex min-h-dvh flex-col bg-slate-950 text-slate-50">
      <MenuPrincipal />
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/perfil" element={<PerfilProspeccao />} />
        <Route path="/resultados" element={<Resultados />} />
      </Routes>
    </div>
  )
}
