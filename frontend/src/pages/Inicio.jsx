import { Radar } from 'lucide-react'
import { Link } from 'react-router'

export default function Inicio() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-14">
      <div className="rounded-2xl border border-divisor bg-superficie px-6 py-10 shadow-xs sm:px-12 sm:py-16">
        <span className="mb-6 inline-grid size-14 place-items-center rounded-xl bg-acao-suave text-acao">
          <Radar aria-hidden="true" className="size-7" />
        </span>
        <h1 className="text-4xl font-bold tracking-tight text-marinho sm:text-6xl">
          RadarLead
        </h1>
        <p className="mt-3 max-w-md text-lg leading-relaxed text-suave sm:text-xl">
          Sistema Inteligente de Prospecção Comercial
        </p>
        <Link
          to="/perfil"
          className="mt-8 inline-flex min-h-11 items-center rounded-lg bg-turquesa px-5 text-sm font-semibold text-marinho transition-colors hover:bg-turquesa/80"
        >
          Abrir perfil de prospecção
        </Link>
      </div>
    </main>
  )
}
