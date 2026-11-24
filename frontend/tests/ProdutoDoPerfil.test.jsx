// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import PerfilProspeccao from '../src/pages/PerfilProspeccao.jsx'

const empresa = { id: 3, nome: 'Empresa', cnpj: '12345678000195', email: 'teste@example.org' }
const produtos = [
  { id: 12, empresa_usuaria_id: 3, nome: 'Consultoria', descricao: null },
  { id: 13, empresa_usuaria_id: 3, nome: 'Treinamento', descricao: null },
]
const perfil = { id: 8, nome: 'Comércio', produto_id: 12 }
const lead = { cnpj: '12345678000195', razao_social: 'Lead retornado', pontuacao: 42, justificativas: [] }
let dadosApi
let enviar

function resposta(status, dados) {
  return new Response(JSON.stringify(dados), { status })
}

beforeEach(() => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
  vi.stubEnv('VITE_RADARLEAD_API_URL', 'http://localhost:8001')
  dadosApi = {
    '/api/empresa-usuaria': () => resposta(200, empresa),
    '/api/produtos': () => resposta(200, { produtos }),
    '/api/perfis': () => resposta(200, { perfis: [perfil] }),
  }
  enviar = vi.fn(() => resposta(201, { perfil, leads: [lead] }))
  vi.stubGlobal('fetch', vi.fn(async (url, opcoes) => {
    const caminho = new URL(url).pathname
    if (caminho === '/api/prospeccoes') return enviar(JSON.parse(opcoes.body))
    return dadosApi[caminho]()
  }))
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

function preencher(rotulo, value) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value } })
}
function abrir(nome = ' comercio ') {
  render(<MemoryRouter><PerfilProspeccao /></MemoryRouter>)
  preencher('Nome do perfil', nome)
  preencher('Pesquisar por atividade ou código CNAE', '6204000')
  fireEvent.click(screen.getByRole('option', { name: /6204-0/ }))
  preencher('Porte empresarial', '3')
  preencher('Município-alvo', '5208707')
  fireEvent.click(screen.getByRole('option', { name: /Goiânia/ }))
}
function consultar() {
  fireEvent.blur(screen.getByLabelText('Nome do perfil'))
}
function buscar() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
}
function escolher(id) {
  preencher('Escolher produto ou serviço', String(id))
}
function campoProduto() {
  return screen.queryByLabelText('Escolher produto ou serviço')
}
async function consultarVinculado() {
  consultar()
  await screen.findByText('Vínculo atual: Consultoria')
}
const confirmarAlteracao = /Alteração de vínculo confirmada/
const ultimaBusca = () => enviar.mock.lastCall[0]

it('sugere perfil pelo nome sem caixa, espaços ou acento e mantém o vínculo por padrão', async () => {
  abrir('  COMERCIO  ')
  expect(fetch).not.toHaveBeenCalled()
  await consultarVinculado()
  expect(campoProduto()).toHaveValue('')
  buscar()
  await screen.findByText(lead.razao_social)
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  expect(ultimaBusca()).toStrictEqual({
    nome: 'COMERCIO', cnaes_desejados: ['6204000'], porte_desejado: 3,
    municipio_alvo_ibge: '5208707', peso_cnae: 50, peso_porte: 25, peso_localizacao: 25,
  })
})

it('habilita associação explícita sem afirmar que o perfil sem correspondência é novo', async () => {
  abrir('Nome sem correspondência')
  consultar()
  await screen.findByText('Nenhum perfil correspondente foi encontrado na consulta.')
  expect(screen.queryByRole('button', { name: 'Remover associação' })).not.toBeInTheDocument()
  escolher(13)
  const pendente = Promise.withResolvers()
  enviar.mockReturnValueOnce(pendente.promise)
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(true)
  expect(ultimaBusca().produto_id).toBe(13)
  expect(screen.queryByText(confirmarAlteracao)).not.toBeInTheDocument()
  await act(async () => pendente.resolve(resposta(201, { perfil: { id: 14, produto_id: 13 }, leads: [lead] })))
  expect(screen.getByText('Vínculo atual: Treinamento')).toBeInTheDocument()
  expect(screen.getByText(confirmarAlteracao)).toBeInTheDocument()
  expect(campoProduto()).toHaveValue('')
})

it.each([13, null])('confirma troca ou remoção explícita com valor %j', async (valor) => {
  abrir()
  await consultarVinculado()
  if (valor === null) fireEvent.click(screen.getByRole('button', { name: 'Remover associação' }))
  else escolher(valor)
  enviar.mockReturnValueOnce(resposta(201, { perfil: { id: 8, produto_id: valor }, leads: [] }))
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(true)
  expect(ultimaBusca().produto_id).toBe(valor)
  await screen.findByText(confirmarAlteracao)
  expect(screen.getByText(valor === null ? 'Perfil geral, sem produto associado.' : 'Vínculo atual: Treinamento')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Cancelar alteração' })).not.toBeInTheDocument()
})

it('preserva perfil geral sem enviar null automaticamente', async () => {
  dadosApi['/api/perfis'] = () => resposta(200, { perfis: [{ ...perfil, produto_id: null }] })
  abrir()
  consultar()
  await screen.findByText('Perfil geral, sem produto associado.')
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it('cancela a alteração pendente e omite a propriedade', async () => {
  abrir()
  await consultarVinculado()
  escolher(13)
  fireEvent.click(screen.getByRole('button', { name: 'Cancelar alteração' }))
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it.each(['associar', 'remover'])('descarta intenção de %s ao alterar o nome', async (intencao) => {
  abrir()
  await consultarVinculado()
  if (intencao === 'associar') escolher(13)
  else fireEvent.click(screen.getByRole('button', { name: 'Remover associação' }))
  preencher('Nome do perfil', 'Outro')
  expect(campoProduto()).not.toBeInTheDocument()
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it('bloqueia alterações quando a correspondência local é ambígua', async () => {
  dadosApi['/api/perfis'] = () => resposta(200, { perfis: [perfil, { ...perfil, id: 9, nome: 'COMERCIO' }] })
  abrir()
  consultar()
  await screen.findByText(/Há mais de um perfil/)
  expect(campoProduto()).not.toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Remover associação' })).not.toBeInTheDocument()
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it('ignora consulta antiga que termina após a troca de nome', async () => {
  const antiga = Promise.withResolvers()
  dadosApi['/api/perfis'] = vi.fn().mockReturnValueOnce(antiga.promise)
    .mockImplementation(() => resposta(200, { perfis: [{ ...perfil, nome: 'Outro', produto_id: 13 }] }))
  abrir()
  consultar()
  await vi.waitFor(() => expect(dadosApi['/api/perfis']).toHaveBeenCalledTimes(1))
  preencher('Nome do perfil', 'Outro')
  consultar()
  await screen.findByText('Vínculo atual: Treinamento')
  await act(async () => antiga.resolve(resposta(200, { perfis: [perfil] })))
  expect(screen.getByText('Vínculo atual: Treinamento')).toBeInTheDocument()
  expect(screen.queryByText('Vínculo atual: Consultoria')).not.toBeInTheDocument()
})

it('orienta cadastro da empresa e permite a busca convencional', async () => {
  dadosApi['/api/empresa-usuaria'] = () => resposta(404, { erro: { codigo: 'nao_encontrado' } })
  abrir()
  consultar()
  expect(await screen.findByRole('link', { name: 'Minha empresa' })).toHaveAttribute('href', '/minha-empresa')
  expect(fetch).toHaveBeenCalledTimes(1)
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it('lista vazia preserva o vínculo cujo produto não está disponível', async () => {
  dadosApi['/api/produtos'] = () => resposta(200, { produtos: [] })
  abrir()
  consultar()
  await screen.findByText('Os dados do produto associado estão indisponíveis.')
  expect(screen.getByRole('link', { name: 'Minha empresa' })).toBeInTheDocument()
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it.each([
  ['/api/perfis', () => resposta(503, {}), /banco de dados está indisponível/],
  ['/api/produtos', () => { throw new TypeError('offline') }, /conectar à API/],
])('trata falha de consulta %s sem impedir busca convencional', async (caminho, falha, mensagem) => {
  dadosApi[caminho] = falha
  abrir()
  consultar()
  expect(await screen.findByRole('alert')).toHaveTextContent(mensagem)
  expect(screen.getByRole('button', { name: 'Tentar consultar vínculo novamente' })).toBeInTheDocument()
  expect(campoProduto()).not.toBeInTheDocument()
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it('explica uma intenção que ficou inválida após atualizar produtos', async () => {
  abrir()
  await consultarVinculado()
  escolher(13)
  dadosApi['/api/produtos'] = () => resposta(200, { produtos: [produtos[0]] })
  fireEvent.click(screen.getByRole('button', { name: 'Atualizar consulta do vínculo' }))
  await screen.findByRole('option', { name: 'Consultoria' })
  buscar()
  expect(screen.getByRole('alert')).toHaveTextContent(/alteração pendente não pode ser aplicada/)
  expect(enviar).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Cancelar alteração' }))
  buscar()
  expect(Object.hasOwn(ultimaBusca(), 'produto_id')).toBe(false)
  await screen.findByText(lead.razao_social)
})

it.each([400, 503, 'rede'])('preserva a escolha após falha no POST %s', async (status) => {
  abrir()
  await consultarVinculado()
  escolher(13)
  if (status === 'rede') enviar.mockRejectedValueOnce(new TypeError('offline'))
  else enviar.mockReturnValueOnce(resposta(status, { erro: { codigo: status === 400 ? 'dados_invalidos' : 'banco_indisponivel', mensagem: 'Falha de associação' } }))
  buscar()
  expect(await screen.findByRole('alert')).toHaveTextContent(status === 'rede' ? /conectar à API/ : 'Falha de associação')
  expect(campoProduto()).toHaveValue('13')
  expect(screen.queryByText(confirmarAlteracao)).not.toBeInTheDocument()
})

it.each([{ id: 8 }, { id: 8, produto_id: 12 }, { id: 90, produto_id: 13 }])(
  'preserva leads sem confirmar vínculo ausente ou divergente %j', async (retornado) => {
    abrir()
    await consultarVinculado()
    escolher(13)
    enviar.mockReturnValueOnce(resposta(201, { perfil: retornado, leads: [lead] }))
    buscar()
    expect(await screen.findByText(lead.razao_social)).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(/não confirmou o vínculo|difere da alteração solicitada/)
    expect(screen.queryByText(confirmarAlteracao)).not.toBeInTheDocument()
  },
)

it('ignora confirmação antiga depois de alterar o nome', async () => {
  abrir()
  await consultarVinculado()
  escolher(13)
  const antiga = Promise.withResolvers()
  enviar.mockReturnValueOnce(antiga.promise)
  buscar()
  preencher('Nome do perfil', 'Outro')
  await act(async () => antiga.resolve(resposta(201, { perfil: { id: 8, produto_id: 13 }, leads: [lead] })))
  expect(screen.queryByText(confirmarAlteracao)).not.toBeInTheDocument()
  expect(screen.queryByText(lead.razao_social)).not.toBeInTheDocument()
})

it('não consulta cadastros nem mostra associação no modo simulado', async () => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'simulado')
  abrir()
  consultar()
  expect(screen.queryByRole('group', { name: 'Produto ou serviço associado' })).not.toBeInTheDocument()
  buscar()
  expect(await screen.findByText(/Empresa Exemplo Gama/)).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
