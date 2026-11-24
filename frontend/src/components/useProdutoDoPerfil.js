import { useEffect, useRef, useState } from 'react'
import { consultarEmpresa } from '../services/empresaUsuariaHttp.js'
import { listarProdutos } from '../services/produtosHttp.js'
import { listarPerfis } from '../services/perfisHttp.js'

const manter = { tipo: 'manter' }
const inicial = { etapa: 'inicial' }

function normalizarNome(nome) {
  return nome.trim().normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

export default function useProdutoDoPerfil() {
  const [consulta, setConsulta] = useState(inicial)
  const [intencao, setIntencao] = useState(manter)
  const [confirmado, setConfirmado] = useState(null)
  const [aviso, setAviso] = useState(null)
  const pendente = useRef(null)

  useEffect(() => () => pendente.current?.abort(), [])

  function mudarNome() {
    pendente.current?.abort()
    setConsulta(inicial)
    setIntencao(manter)
    setConfirmado(null)
    setAviso(null)
  }

  async function consultar(nome) {
    if (!nome.trim()) return
    pendente.current?.abort()
    const controle = new AbortController()
    pendente.current = controle
    setConsulta({ etapa: 'carregando' })
    const { signal } = controle
    try {
      const empresa = await consultarEmpresa(signal)
      if (signal.aborted) return
      if (!empresa) {
        setConsulta({ etapa: 'semEmpresa' })
        return
      }
      const [produtos, perfis] = await Promise.all([
        listarProdutos(signal),
        listarPerfis(signal),
      ])
      if (signal.aborted) return
      const correspondencias = perfis.filter((perfil) => normalizarNome(perfil.nome) === normalizarNome(nome))
      setConsulta({
        etapa: correspondencias.length > 1 ? 'ambigua' : 'pronta',
        produtos,
        perfil: correspondencias[0] ?? null,
      })
    } catch (erro) {
      if (!signal.aborted) setConsulta({ etapa: 'erro', mensagem: erro.message })
    }
  }

  const perfil = confirmado ?? (consulta.etapa === 'pronta' ? consulta.perfil : null)
  const produtos = consulta.produtos ?? []
  const podeEditar = consulta.etapa === 'pronta'
  const intencaoValida = intencao.tipo === 'manter' || (podeEditar && (
    intencao.tipo === 'remover' ? perfil?.produto_id != null :
      produtos.some(({ id }) => id === intencao.id)
  ))

  function escolher(nova) {
    setIntencao(nova)
    setAviso(null)
  }

  function preparar(dados) {
    if (!intencaoValida) {
      setAviso({ erro: true, texto: 'A alteração pendente não pode ser aplicada. Atualize a consulta, corrija ou cancele a alteração.' })
      return null
    }
    setAviso(null)
    if (intencao.tipo === 'manter') return dados
    return { ...dados, produto_id: intencao.tipo === 'remover' ? null : intencao.id }
  }

  function confirmar(retorno, dados) {
    setConfirmado(retorno)
    if (!Object.hasOwn(dados, 'produto_id')) return
    if (!retorno || retorno.produto_id !== dados.produto_id || (perfil && perfil.id !== retorno.id)) {
      setAviso({
        erro: true,
        texto: retorno
          ? 'O perfil ou vínculo retornado pela API difere da alteração solicitada.'
          : 'A API não confirmou o vínculo do perfil. Os resultados da busca continuam disponíveis.',
      })
      return
    }
    setAviso({ erro: false, texto: 'Alteração de vínculo confirmada pela API.' })
    setIntencao(manter)
  }

  return { consulta, consultar, mudarNome, perfil, produtos, podeEditar, intencao, escolher, preparar, confirmar, aviso }
}
