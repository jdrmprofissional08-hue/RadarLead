import { useEffect, useRef, useState } from 'react'
import { coordenadasValidas } from '../utils/origemProspeccao.js'

async function carregarCatalogo() {
  const resposta = await fetch(`${import.meta.env.BASE_URL}dados-locais/coordenadas-municipios.json`)
  if (resposta.status === 404) throw new Error('Catálogo local não encontrado.')
  if (!resposta.ok) throw new Error('O catálogo local está indisponível.')

  const dados = await resposta.json().catch(() => null)
  const entradas = dados && typeof dados === 'object' && !Array.isArray(dados) ? Object.entries(dados) : []
  if (!entradas.length || entradas.some(([codigo, par]) => !/^[0-9]{7}$/.test(codigo) || !coordenadasValidas(par))) {
    throw new Error('O catálogo local é inválido. Gere o arquivo novamente.')
  }
  return dados
}

export default function useCatalogoCoordenadas(ativo) {
  const requisicao = useRef(null)
  const [tentativa, setTentativa] = useState(0)
  const [estado, setEstado] = useState({ etapa: 'carregando' })

  useEffect(() => {
    if (!ativo) return
    let atual = true
    requisicao.current ??= carregarCatalogo().catch((erro) => {
      requisicao.current = null
      throw erro
    })
    requisicao.current.then(
      (dados) => { if (atual) setEstado({ etapa: 'pronto', dados }) },
      (erro) => {
        if (atual) setEstado({
          etapa: 'erro',
          mensagem: erro instanceof TypeError ? 'Falha ao carregar o catálogo local.' : erro.message,
        })
      },
    )
    return () => { atual = false }
  }, [ativo, tentativa])

  return {
    ...estado,
    tentarNovamente() {
      setEstado({ etapa: 'carregando' })
      setTentativa((valor) => valor + 1)
    },
  }
}
