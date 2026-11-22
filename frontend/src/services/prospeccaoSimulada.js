import { empresasSimuladas } from '../data/resultadosSimulados.js'

const formatoPontos = new Intl.NumberFormat('pt-BR', { maximumSignificantDigits: 21 })

export async function buscarEmpresasSimuladas(perfil) {
  // A espera local permite exercitar o estado de carregamento.
  await new Promise((resolver) => setTimeout(resolver, 500))

  // A elegibilidade real poderá usar CNAEs secundários e relacionados,
  // situação cadastral e distância. A base fictícia usa só o CNAE principal.
  const elegiveis = empresasSimuladas.filter(({ cnae_principal }) =>
    perfil.cnaes_desejados.includes(cnae_principal),
  )

  return elegiveis.map((empresa) => {
    const criterios = [
      { nome: 'CNAE', compativel: true, peso: perfil.peso_cnae },
      { nome: 'Porte', compativel: empresa.porte === perfil.porte_desejado, peso: perfil.peso_porte },
      { nome: 'Município', compativel: empresa.municipio_ibge === perfil.municipio_alvo_ibge, peso: perfil.peso_localizacao },
    ]
    let pontuacao = 0
    const justificativas = criterios.map(({ nome, compativel, peso }) => {
      const pontos = compativel ? peso : 0
      pontuacao += pontos
      const unidade = pontos === 1 ? 'ponto' : 'pontos'
      return `${nome} ${compativel ? 'compatível' : 'diferente'}: +${formatoPontos.format(pontos)} ${unidade}`
    })
    if (!Number.isFinite(pontuacao)) {
      throw new RangeError('A soma dos pontos não pôde ser representada.')
    }
    return { ...empresa, pontuacao, justificativas }
  }).filter(({ pontuacao }) => pontuacao > 0)
}
