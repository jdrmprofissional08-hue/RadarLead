import { LogOut, Radar } from 'lucide-react'
import { NavLink } from 'react-router'

export default function MenuPrincipal() {
  return (
    <header className="bg-marinho text-white">
      <nav aria-label="Menu principal" className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-7 gap-y-3 px-4 py-3 sm:px-6">
        <span className="inline-flex items-center gap-2 font-semibold tracking-tight">
          <Radar aria-hidden="true" className="size-5 text-turquesa" />
          RadarLead
        </span>
        <ul className="flex min-w-0 flex-1 basis-full flex-wrap items-center gap-2 sm:basis-auto">
          {[
            { caminho: '/', rotulo: 'Início' },
            { caminho: '/minha-empresa', rotulo: 'Minha empresa' },
            { caminho: '/perfil', rotulo: 'Perfil de Prospecção' },
          ].map(({ caminho, rotulo }) => (
            <li key={caminho}>
              <NavLink
                to={caminho}
                end
                className="block rounded-t-md border-b-2 border-transparent px-3 py-2 text-sm font-medium text-white/80 hover:bg-white/10 hover:text-white focus-visible:outline-turquesa aria-[current=page]:border-turquesa aria-[current=page]:bg-white/5 aria-[current=page]:text-white"
              >
                {rotulo}
              </NavLink>
            </li>
          ))}
          <li title="Disponível quando houver autenticação" className="sm:ml-auto">
            <button
              type="button"
              disabled
              aria-describedby="aviso-sair"
              className="inline-flex cursor-not-allowed items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-white/70"
            >
              <LogOut aria-hidden="true" className="size-4 shrink-0" />
              Sair
            </button>
            <span id="aviso-sair" className="sr-only">
              Disponível quando houver autenticação
            </span>
          </li>
        </ul>
      </nav>
    </header>
  )
}
