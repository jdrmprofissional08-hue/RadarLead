import { obterUrlApi } from './urlApi.js'

const errosHttp = {
  400: 'Dados inválidos. Confira o nome, o CNPJ e o e-mail.',
  409: 'O CNPJ ou o e-mail já está em uso por outra empresa.',
  503: 'O banco de dados está indisponível. Tente novamente mais tarde.',
}

async function solicitarEmpresa(opcoes) {
  const { method } = opcoes
  let resposta
  try {
    resposta = await fetch(`${obterUrlApi()}/api/empresa-usuaria`, opcoes)
  } catch (erro) {
    if (opcoes.signal?.aborted) throw erro
    throw new Error('Não foi possível conectar à API do RadarLead. Verifique a conexão e tente novamente.')
  }
  const corpo = await resposta.json().catch(() => null)

  if (method === 'GET' && resposta.status === 404 && corpo?.erro?.codigo === 'nao_encontrado') {
    return null
  }
  const sucesso = resposta.status === 200 || (method === 'PUT' && resposta.status === 201)
  if (!sucesso) {
    throw new Error(errosHttp[resposta.status] ?? `A API não concluiu a operação (HTTP ${resposta.status}).`)
  }

  // Até a publicação do PUT, assume-se que ele retorna o mesmo objeto plano do GET.
  if (!Number.isInteger(corpo?.id) || !['nome', 'cnpj', 'email'].every((campo) =>
    typeof corpo[campo] === 'string' && corpo[campo].trim(),
  )) {
    throw new Error('A API retornou dados inesperados para a empresa usuária.')
  }
  const { id, nome, cnpj, email } = corpo
  return { id, nome, cnpj, email }
}

export function consultarEmpresa(signal) {
  return solicitarEmpresa({ method: 'GET', signal })
}

export function salvarEmpresa({ nome, cnpj, email }) {
  return solicitarEmpresa({
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome, cnpj, email }),
  })
}
