// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import MinhaEmpresa from '../src/pages/MinhaEmpresa.jsx'

const empresa = { id: 1, nome: 'Empresa de teste', cnpj: '12345678000195', email: 'contato@example.org' }
const produto = { id: 8, empresa_usuaria_id: 1, nome: 'Consultoria', descricao: 'Implantação de sistemas.' }
const url = 'http://localhost:8001/api/produtos'

function resposta(status, dados) {
  return new Response(JSON.stringify(dados), { status })
}
function secao() {
  return within(screen.getByRole('region', { name: 'Produtos e serviços' }))
}
function nome() {
  return secao().getByLabelText('Nome do produto ou serviço')
}
function descricao() {
  return secao().getByLabelText('Descrição (opcional)')
}
function salvar() {
  return secao().getByRole('button', { name: 'Salvar produto ou serviço' })
}
async function abrir(produtos = []) {
  fetch.mockResolvedValueOnce(resposta(200, empresa)).mockResolvedValueOnce(resposta(200, { produtos }))
  render(<MinhaEmpresa />)
  await screen.findByLabelText('Nome do produto ou serviço')
}

beforeEach(() => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
  vi.stubEnv('VITE_RADARLEAD_API_URL', 'http://localhost:8001/')
  vi.stubGlobal('fetch', vi.fn())
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

it('lista produtos, descrição e alternativa para descrição nula', async () => {
  await abrir([produto, { ...produto, id: 9, nome: 'Treinamento', descricao: null }])
  expect(secao().getByText('Consultoria')).toBeInTheDocument()
  expect(secao().getByText(produto.descricao)).toBeInTheDocument()
  expect(secao().getByText('Treinamento')).toBeInTheDocument()
  expect(secao().getByText('Sem descrição.')).toBeInTheDocument()
  expect(fetch).toHaveBeenNthCalledWith(2, url, expect.objectContaining({ method: 'GET' }))
})

it('mostra carregamento e só exibe lista vazia após resposta válida', async () => {
  const lista = Promise.withResolvers()
  fetch.mockResolvedValueOnce(resposta(200, empresa)).mockReturnValueOnce(lista.promise)
  render(<MinhaEmpresa />)
  expect(await screen.findByText('Consultando produtos e serviços…')).toBeInTheDocument()
  expect(secao().queryByText('Nenhum produto ou serviço cadastrado.')).not.toBeInTheDocument()
  await act(async () => { lista.resolve(resposta(200, { produtos: [] })) })
  expect(secao().getByText('Nenhum produto ou serviço cadastrado.')).toBeInTheDocument()
})

it('valida o nome obrigatório e impede o POST', async () => {
  await abrir()
  fireEvent.change(nome(), { target: { value: '   ' } })
  fireEvent.click(salvar())
  expect(nome()).toHaveFocus()
  expect(nome()).toHaveAccessibleDescription('Informe um nome de até 200 caracteres.')
  expect(fetch).toHaveBeenCalledTimes(2)
})

it('omite a descrição em branco e o ID da empresa, bloqueia envios repetidos e só confirma após 201', async () => {
  await abrir([produto])
  const criacao = Promise.withResolvers()
  fetch.mockReturnValueOnce(criacao.promise)
  fireEvent.change(nome(), { target: { value: ' Treinamento ' } })
  fireEvent.change(descricao(), { target: { value: '  ' } })
  const form = salvar().closest('form')
  fireEvent.submit(form)
  fireEvent.submit(form)
  expect(salvar()).toBeDisabled()
  expect(fetch).toHaveBeenCalledTimes(3)
  expect(fetch).toHaveBeenLastCalledWith(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"nome":"Treinamento"}',
  })
  expect(secao().queryByText(/cadastrado com sucesso/)).not.toBeInTheDocument()
  await act(async () => { criacao.resolve(resposta(201, { ...produto, id: 9, nome: 'Treinamento', descricao: null })) })
  expect(secao().getByText(/cadastrado com sucesso/)).toBeInTheDocument()
  expect(secao().getAllByRole('listitem')).toHaveLength(2)
  expect(secao().getByText('Treinamento')).toBeInTheDocument()
  expect(nome()).toHaveValue('')
  expect(salvar()).toBeEnabled()
})

it.each([
  [400, 'dados_invalidos', /Dados inválidos/],
  [404, 'nao_encontrado', /empresa atual não foi encontrada/],
  [409, 'duplicado', /Já existe um produto ou serviço/],
  [503, 'banco_indisponivel', /banco de dados está indisponível/],
  [201, null, /dados inesperados/],
])('trata POST %i (%s) e preserva os campos', async (status, codigo, mensagem) => {
  await abrir()
  fetch.mockResolvedValueOnce(resposta(status, { erro: { codigo } }))
  fireEvent.change(nome(), { target: { value: ' Treinamento ' } })
  fireEvent.change(descricao(), { target: { value: ' Capacitação ' } })
  fireEvent.click(salvar())
  expect(fetch).toHaveBeenLastCalledWith(url, expect.objectContaining({
    body: '{"nome":"Treinamento","descricao":"Capacitação"}',
  }))
  expect(await secao().findByRole('alert')).toHaveTextContent(mensagem)
  expect(nome()).toHaveValue(' Treinamento ')
  expect(descricao()).toHaveValue(' Capacitação ')
  expect(secao().queryByText(/cadastrado com sucesso/)).not.toBeInTheDocument()
})

it('permite repetir consulta após falha de rede e 503, sem apresentar lista vazia nesses erros', async () => {
  fetch.mockResolvedValueOnce(resposta(200, empresa)).mockRejectedValueOnce(new TypeError('offline'))
    .mockResolvedValueOnce(resposta(503, { erro: { codigo: 'banco_indisponivel' } }))
    .mockResolvedValueOnce(resposta(200, { produtos: [produto] }))
  render(<MinhaEmpresa />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/conectar à API/)
  expect(secao().queryByText('Nenhum produto ou serviço cadastrado.')).not.toBeInTheDocument()
  fireEvent.click(secao().getByRole('button', { name: 'Tentar consultar produtos novamente' }))
  expect(await secao().findByRole('alert')).toHaveTextContent(/banco de dados está indisponível/)
  fireEvent.click(secao().getByRole('button', { name: 'Tentar consultar produtos novamente' }))
  expect(await secao().findByText('Consultoria')).toBeInTheDocument()
})

it('aguarda o primeiro cadastro da empresa antes de pedir produtos', async () => {
  fetch.mockResolvedValueOnce(resposta(404, { erro: { codigo: 'nao_encontrado' } }))
  render(<MinhaEmpresa />)
  expect(await screen.findByText(/Cadastre primeiro a empresa/)).toBeInTheDocument()
  expect(secao().queryByLabelText('Nome do produto ou serviço')).not.toBeInTheDocument()
  expect(secao().queryByText('Nenhum produto ou serviço cadastrado.')).not.toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
  fetch.mockResolvedValueOnce(resposta(201, empresa)).mockResolvedValueOnce(resposta(200, { produtos: [] }))
  for (const [rotulo, value] of [['Nome da empresa', empresa.nome], ['CNPJ', empresa.cnpj], ['E-mail', empresa.email]]) {
    fireEvent.change(screen.getByLabelText(rotulo), { target: { value } })
  }
  fireEvent.click(screen.getByRole('button', { name: 'Salvar empresa' }))
  expect(await secao().findByText('Nenhum produto ou serviço cadastrado.')).toBeInTheDocument()
  expect(fetch).toHaveBeenNthCalledWith(3, url, expect.objectContaining({ method: 'GET' }))
})

it.each(['rede', '503'])('bloqueia produtos quando a consulta da empresa falha por %s', async (falha) => {
  if (falha === 'rede') fetch.mockRejectedValueOnce(new TypeError('offline'))
  else fetch.mockResolvedValueOnce(resposta(503, { erro: { codigo: 'banco_indisponivel' } }))
  render(<MinhaEmpresa />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Falha na consulta.')
  expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeInTheDocument()
  expect(secao().getByText(/após confirmar o cadastro/)).toBeInTheDocument()
  expect(secao().queryByLabelText('Nome do produto ou serviço')).not.toBeInTheDocument()
  expect(fetch).toHaveBeenCalledTimes(1)
})

it.each(['', 'simulado'])('não consulta nem simula persistência com modo %j', (modo) => {
  vi.stubEnv('VITE_RADARLEAD_MODO', modo)
  render(<MinhaEmpresa />)
  expect(secao().getByText(/exigem a API do RadarLead/)).toBeInTheDocument()
  expect(secao().queryByRole('list')).not.toBeInTheDocument()
  expect(secao().queryByLabelText('Nome do produto ou serviço')).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
