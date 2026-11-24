import { adaptarVinculoPerfil } from './perfisHttp.js'
import { obterUrlApi } from './urlApi.js'

const erroResposta = 'A API retornou uma resposta de prospecção inválida.'

export class ErroProspeccaoHttp extends Error {}

export async function buscarEmpresasHttp(perfil) {
  let resposta
  try {
    resposta = await fetch(`${obterUrlApi()}/api/prospeccoes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(perfil),
    })
  } catch {
    throw new ErroProspeccaoHttp('Não foi possível conectar à API do RadarLead. Verifique se o servidor está em execução e se a origem do frontend está liberada.')
  }

  const dados = await resposta.json().catch(() => null)
  if (!resposta.ok) {
    const mensagem = dados?.erro?.mensagem
    throw new ErroProspeccaoHttp(
      typeof mensagem === 'string' && mensagem.trim()
        ? mensagem.trim()
        : `A busca falhou na API do RadarLead (HTTP ${resposta.status}).`,
    )
  }

  if (resposta.status !== 201 || !Array.isArray(dados?.leads)) {
    throw new ErroProspeccaoHttp(erroResposta)
  }

  const leads = dados.leads.map((lead) => {
    if (
      !lead || typeof lead.cnpj !== 'string' || typeof lead.razao_social !== 'string' ||
      !Number.isFinite(lead.pontuacao) || !Array.isArray(lead.justificativas) ||
      !lead.justificativas.every((texto) => typeof texto === 'string') ||
      (lead.porte != null && !Number.isInteger(lead.porte)) ||
      [lead.cnae_principal, lead.porte_descricao, lead.municipio_ibge, lead.status]
        .some((valor) => valor != null && typeof valor !== 'string')
    ) {
      throw new ErroProspeccaoHttp(erroResposta)
    }

    const {
      cnpj, razao_social, pontuacao, justificativas,
      cnae_principal, porte, porte_descricao, municipio_ibge, status,
    } = lead
    return { cnpj, razao_social, pontuacao, justificativas, cnae_principal, porte, porte_descricao, municipio_ibge, status }
  })
  return { leads, perfil: adaptarVinculoPerfil(dados.perfil) }
}
