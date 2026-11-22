import { useRef, useState } from 'react'
import FormularioPerfil from '../components/FormularioPerfil.jsx'
import ListaResultados from '../components/ListaResultados.jsx'
import { buscarEmpresasSimuladas } from '../services/prospeccaoSimulada.js'

export default function PerfilProspeccao() {
  const [busca, setBusca] = useState({ etapa: 'inicial' })
  const buscaAtual = useRef(0)

  function invalidarBusca() {
    buscaAtual.current += 1
    setBusca({ etapa: 'inicial' })
  }

  async function buscar(dados) {
    const idBusca = ++buscaAtual.current
    setBusca({ etapa: 'carregando' })

    try {
      const resultados = await buscarEmpresasSimuladas(dados)
      if (idBusca === buscaAtual.current) {
        setBusca({ etapa: 'concluida', resultados })
      }
    } catch {
      if (idBusca === buscaAtual.current) {
        setBusca({ etapa: 'erro' })
      }
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
        Perfil de Prospecção
      </h1>
      <p className="mt-2 text-sm text-slate-300">
        Dados simulados. A busca usa uma base fictícia.
      </p>
      <FormularioPerfil
        onBuscar={buscar}
        onAlterar={invalidarBusca}
        buscando={busca.etapa === 'carregando'}
      />
      <div role="status" className="mt-4 text-sm text-slate-300">
        {busca.etapa === 'carregando' && 'Buscando empresas…'}
        {busca.etapa === 'concluida' && busca.resultados.length === 0 && (
          <span className="sr-only">Nenhuma empresa encontrada</span>
        )}
        {busca.etapa === 'concluida' && busca.resultados.length > 0 && (
          <span className="sr-only">Busca concluída. Resultados abaixo do formulário.</span>
        )}
      </div>
      {busca.etapa === 'erro' && (
        <p role="alert" className="text-sm text-rose-300">
          Não foi possível concluir a busca simulada. Confira os critérios e tente novamente.
        </p>
      )}
      {busca.etapa === 'concluida' && (
        <section aria-labelledby="titulo-resultados" className="mt-8 border-t border-slate-800 pt-6">
          <h2 id="titulo-resultados" className="text-2xl font-semibold">Resultados da busca</h2>
          <ListaResultados resultados={busca.resultados} />
        </section>
      )}
    </main>
  )
}
