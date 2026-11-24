import { obterUrlApi } from './urlApi.js'

export const mensagemBancoIndisponivel = 'O banco de dados está indisponível. Tente novamente mais tarde.'

export async function solicitarCadastro(caminho, opcoes) {
  let resposta
  try {
    resposta = await fetch(`${obterUrlApi()}${caminho}`, opcoes)
  } catch (erro) {
    if (opcoes.signal?.aborted) throw erro
    throw new Error('Não foi possível conectar à API do RadarLead. Verifique a conexão e tente novamente.')
  }

  const corpo = await resposta.json().catch(() => null)
  return { status: resposta.status, corpo }
}
