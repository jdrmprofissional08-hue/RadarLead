import { LogOut } from 'lucide-react'
import { NavLink } from 'react-router'

export default function MenuPrincipal() {
  return (
    <header className="border-b border-slate-800">
      <nav aria-label="Menu principal" className="mx-auto max-w-5xl px-4 py-3">
        <ul className="flex flex-wrap gap-2">
          {[
            { caminho: '/', rotulo: 'Início' },
            { caminho: '/perfil', rotulo: 'Perfil de Prospecção' },
            { caminho: '/resultados', rotulo: 'Resultados' },
          ].map(({ caminho, rotulo }) => (
            <li key={caminho}>
              <NavLink
                to={caminho}
                end
                className="block rounded-md px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 aria-[current=page]:bg-emerald-400/10 aria-[current=page]:text-emerald-400"
              >
                {rotulo}
              </NavLink>
            </li>
          ))}
          <li className="flex flex-wrap items-center gap-x-2 sm:ml-auto">
            <button
              type="button"
              disabled
              aria-describedby="aviso-sair"
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-slate-400"
            >
              <LogOut aria-hidden="true" className="size-4 shrink-0" />
              Sair
            </button>
            <span id="aviso-sair" className="text-xs text-slate-400">
              Disponível quando houver autenticação
            </span>
          </li>
        </ul>
      </nav>
    </header>
  )
}
