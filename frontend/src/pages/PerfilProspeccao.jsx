import { useRef, useState } from 'react'
import FormularioPerfil from '../components/FormularioPerfil.jsx'
import ListaResultados from '../components/ListaResultados.jsx'
import { obterServicoProspeccao } from '../services/prospeccao.js'
import { ErroProspeccaoHttp } from '../services/prospeccaoHttp.js'

export default function PerfilProspeccao() {
  const [busca, setBusca] = useState({ etapa: 'inicial' })
  const buscaAtual = useRef(0)
  const { modo, buscarEmpresas } = obterServicoProspeccao()

  function invalidarBusca() {
    buscaAtual.current += 1
    setBusca({ etapa: 'inicial' })
  }

  async function buscar(dados) {
    const idBusca = ++buscaAtual.current
    setBusca({ etapa: 'carregando' })

    try {
      const resultados = await buscarEmpresas(dados)
      if (idBusca === buscaAtual.current) {
        setBusca({ etapa: 'concluida', resultados })
      }
    } catch (erro) {
      if (idBusca === buscaAtual.current) {
        const mensagem = modo === 'simulado'
          ? 'Não foi possível concluir a busca simulada. Confira os critérios e tente novamente.'
          : erro instanceof ErroProspeccaoHttp
            ? erro.message
            : 'Não foi possível concluir a busca pela API. Tente novamente.'
        setBusca({ etapa: 'erro', mensagem })
      }
    }
  }

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
      <h1 className="text-3xl font-bold tracking-tight text-marinho sm:text-4xl">
        Perfil de Prospecção
      </h1>
      <p className="mt-3 text-sm text-suave">
        {modo === 'simulado' && 'Dados simulados. A busca usa uma base fictícia.'}
        {modo === 'http' && 'Busca pela API do RadarLead. No modo demo do servidor, os dados são fictícios.'}
        {modo !== 'simulado' && modo !== 'http' && 'Modo de busca inválido. Verifique a configuração.'}
      </p>
      <FormularioPerfil
        onBuscar={buscar}
        onAlterar={invalidarBusca}
        buscando={busca.etapa === 'carregando'}
      />
      <div role="status" className="text-sm text-acao">
        {busca.etapa === 'carregando' && (
          <p className="mt-4 rounded-lg border border-divisor bg-acao-suave px-4 py-3 font-medium">
            Buscando empresas…
          </p>
        )}
        {busca.etapa === 'concluida' && busca.resultados.length === 0 && (
          <span className="sr-only">Nenhuma empresa encontrada</span>
        )}
        {busca.etapa === 'concluida' && busca.resultados.length > 0 && (
          <span className="sr-only">Busca concluída. Resultados abaixo do formulário.</span>
        )}
      </div>
      {busca.etapa === 'erro' && (
        <p role="alert" className="mt-4 rounded-lg border border-erro/25 bg-erro-suave px-4 py-3 text-sm font-medium text-erro">
          {busca.mensagem}
        </p>
      )}
      {busca.etapa === 'concluida' && (
        <section aria-labelledby="titulo-resultados" className="mt-8 border-t border-divisor pt-6">
          <h2 id="titulo-resultados" className="text-2xl font-semibold tracking-tight text-marinho">Resultados da busca</h2>
          <ListaResultados resultados={busca.resultados} />
        </section>
      )}
    </main>
  )
}
