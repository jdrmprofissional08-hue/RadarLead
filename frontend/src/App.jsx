import { Route, Routes } from 'react-router'
import MenuPrincipal from './components/MenuPrincipal.jsx'
import Inicio from './pages/Inicio.jsx'
import MinhaEmpresa from './pages/MinhaEmpresa.jsx'
import PerfilProspeccao from './pages/PerfilProspeccao.jsx'
import Resultados from './pages/Resultados.jsx'

export default function App() {
  return (
    <div className="flex min-h-dvh flex-col bg-fundo text-texto">
      <MenuPrincipal />
      <Routes>
        <Route path="/" element={<Inicio />} />
        <Route path="/minha-empresa" element={<MinhaEmpresa />} />
        <Route path="/perfil" element={<PerfilProspeccao />} />
        <Route path="/resultados" element={<Resultados />} />
      </Routes>
    </div>
  )
}
