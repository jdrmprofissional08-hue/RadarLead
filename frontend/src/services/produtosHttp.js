import { mensagemBancoIndisponivel, solicitarCadastro } from './cadastroHttp.js'

const caminho = '/api/produtos'
const errosHttp = {
  400: 'Dados inválidos. Confira o nome e a descrição do produto.',
  409: 'Já existe um produto ou serviço com esse nome.',
  503: mensagemBancoIndisponivel,
}

function exigirStatus(status, corpo, esperado) {
  if (status === esperado) return
  if (status === 404 && corpo?.erro?.codigo === 'nao_encontrado') {
    throw new Error('A empresa atual não foi encontrada. Verifique o cadastro da empresa.')
  }
  throw new Error(errosHttp[status] ?? `A API não concluiu a operação de produtos (HTTP ${status}).`)
}

function adaptarProduto(produto) {
  if (
    !Number.isInteger(produto?.id) || produto.id <= 0 ||
    !Number.isInteger(produto.empresa_usuaria_id) || produto.empresa_usuaria_id <= 0 ||
    typeof produto.nome !== 'string' || !produto.nome.trim() ||
    (produto.descricao !== null && typeof produto.descricao !== 'string')
  ) {
    throw new Error('A API retornou dados inesperados para os produtos.')
  }
  const { id, empresa_usuaria_id, nome, descricao } = produto
  return { id, empresa_usuaria_id, nome, descricao }
}

export async function listarProdutos(signal) {
  const { status, corpo } = await solicitarCadastro(caminho, { method: 'GET', signal })
  exigirStatus(status, corpo, 200)
  if (!Array.isArray(corpo?.produtos)) throw new Error('A API retornou uma lista de produtos inválida.')
  return corpo.produtos.map(adaptarProduto)
}

export async function cadastrarProduto({ nome, descricao }) {
  const { status, corpo } = await solicitarCadastro(caminho, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(descricao ? { nome, descricao } : { nome }),
  })
  exigirStatus(status, corpo, 201)
  return adaptarProduto(corpo)
}
