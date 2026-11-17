import { Radar } from 'lucide-react'

export default function Inicio() {
  return (
    <main className="grid flex-1 place-items-center px-6 py-12 text-center">
      <div>
        <Radar
          aria-hidden="true"
          className="mx-auto mb-6 size-12 text-emerald-400"
        />
        <h1 className="text-5xl font-bold tracking-tight sm:text-7xl">
          RadarLead
        </h1>
        <p className="mt-4 text-base text-slate-300 sm:text-xl">
          Sistema Inteligente de Prospecção Comercial
        </p>
      </div>
    </main>
  )
}
