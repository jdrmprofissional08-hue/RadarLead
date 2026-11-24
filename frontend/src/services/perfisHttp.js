import { mensagemBancoIndisponivel, solicitarCadastro } from './cadastroHttp.js'

export function adaptarVinculoPerfil(perfil) {
  if (!Number.isSafeInteger(perfil?.id) || perfil.id <= 0) return null
  const { id, produto_id } = perfil
  if (produto_id !== null && (!Number.isSafeInteger(produto_id) || produto_id <= 0)) return null
  return { id, produto_id }
}

export async function listarPerfis(signal) {
  const { status, corpo } = await solicitarCadastro('/api/perfis', { method: 'GET', signal })
  if (status === 503) throw new Error(mensagemBancoIndisponivel)
  if (status !== 200) throw new Error(`Não foi possível consultar os perfis (HTTP ${status}).`)
  if (!Array.isArray(corpo?.perfis)) throw new Error('A API retornou uma lista de perfis inválida.')

  return corpo.perfis.map((perfil) => {
    const vinculo = adaptarVinculoPerfil(perfil)
    if (!vinculo || typeof perfil.nome !== 'string' || !perfil.nome.trim()) {
      throw new Error('A API retornou dados de vínculo incompletos na lista de perfis.')
    }
    return { ...vinculo, nome: perfil.nome }
  })
}
