// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.jsx'
import MinhaEmpresa from '../src/pages/MinhaEmpresa.jsx'

const empresa = { id: 42, nome: 'Empresa de teste', cnpj: '12345678000195', email: 'contato@example.org' }
const ausente = { erro: { codigo: 'nao_encontrado', mensagem: 'Empresa usuária não cadastrada.' } }
const endpoint = 'http://localhost:8001/api/empresa-usuaria'

function resposta(status, dados) {
  return new Response(JSON.stringify(dados), { status })
}
function preencher(rotulo, value) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value } })
}
function preencherEmpresa() {
  preencher('Nome da empresa', ' Empresa de teste ')
  preencher('CNPJ', '12.345.678/0001-95')
  preencher('E-mail', 'contato@example.org')
}
function salvar() {
  fireEvent.click(screen.getByRole('button', { name: 'Salvar empresa' }))
}

beforeEach(() => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
  vi.stubEnv('VITE_RADARLEAD_API_URL', 'http://localhost:8001/')
  vi.stubGlobal('fetch', vi.fn((url) => {
    if (url === 'http://localhost:8001/api/produtos') return Promise.resolve(resposta(200, { produtos: [] }))
    throw new Error('Requisição não prevista: ' + url)
  }))
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

it('abre Minha empresa pelo menu, mostra o aviso e consulta o cadastro existente', async () => {
  fetch.mockResolvedValueOnce(resposta(200, empresa))
  render(<MemoryRouter><App /></MemoryRouter>)
  fireEvent.click(within(screen.getByRole('navigation', { name: 'Menu principal' })).getByRole('link', { name: 'Minha empresa' }))
  expect(screen.getByRole('heading', { name: 'Minha empresa' })).toBeInTheDocument()
  expect(screen.getByText('Modo demonstração — sem autenticação de usuários')).toBeInTheDocument()
  expect(await screen.findByDisplayValue(empresa.nome)).toBeInTheDocument()
  expect(screen.getByLabelText('CNPJ')).toHaveValue(empresa.cnpj)
  expect(screen.getByLabelText('E-mail')).toHaveValue(empresa.email)
  expect(fetch).toHaveBeenNthCalledWith(1, endpoint, expect.objectContaining({ method: 'GET' }))
})

it('exibe carregamento até o GET confirmar a ausência do cadastro', async () => {
  const consulta = Promise.withResolvers()
  fetch.mockReturnValueOnce(consulta.promise)
  render(<MinhaEmpresa />)
  expect(screen.getByRole('status')).toHaveTextContent('Consultando empresa usuária')
  expect(screen.queryByLabelText('Nome da empresa')).not.toBeInTheDocument()
  await act(async () => { consulta.resolve(resposta(404, ausente)) })
  expect(screen.getByText(/Nenhuma empresa cadastrada/)).toBeInTheDocument()
  expect(screen.getByLabelText('Nome da empresa')).toHaveValue('')
})

it('envia CNPJ normalizado sem ID e só confirma a criação após o PUT 201', async () => {
  const gravacao = Promise.withResolvers()
  fetch.mockResolvedValueOnce(resposta(404, ausente)).mockReturnValueOnce(gravacao.promise)
  render(<MinhaEmpresa />)
  await screen.findByLabelText('Nome da empresa')
  preencherEmpresa()
  salvar()
  expect(fetch).toHaveBeenLastCalledWith(endpoint, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome: empresa.nome, cnpj: empresa.cnpj, email: empresa.email }),
  })
  expect(screen.getByRole('button', { name: 'Salvar empresa' })).toBeDisabled()
  expect(screen.getByRole('status')).toHaveTextContent('Salvando empresa')
  expect(screen.queryByText(/salvos com sucesso/)).not.toBeInTheDocument()
  await act(async () => { gravacao.resolve(resposta(201, empresa)) })
  expect(screen.getByText('Dados da empresa salvos com sucesso.')).toBeInTheDocument()
  expect(screen.queryByText(/Nenhuma empresa cadastrada/)).not.toBeInTheDocument()
  expect(screen.getByLabelText('CNPJ')).toHaveValue(empresa.cnpj)
})

it('permite atualizar com PUT 200 e usa os dados devolvidos pelo servidor', async () => {
  fetch.mockResolvedValueOnce(resposta(200, empresa))
    .mockResolvedValueOnce(resposta(200, { produtos: [] }))
    .mockResolvedValueOnce(resposta(200, { ...empresa, nome: 'Nome confirmado' }))
  render(<MinhaEmpresa />)
  await screen.findByDisplayValue(empresa.nome)
  preencher('Nome da empresa', 'Nome atualizado')
  salvar()
  expect(await screen.findByDisplayValue('Nome confirmado')).toBeInTheDocument()
  expect(screen.getByText('Dados da empresa salvos com sucesso.')).toBeInTheDocument()
})

it('associa os erros de nome, dígitos do CNPJ e e-mail aos campos e impede o PUT', async () => {
  fetch.mockResolvedValueOnce(resposta(404, ausente))
  render(<MinhaEmpresa />)
  await screen.findByLabelText('Nome da empresa')
  preencher('Nome da empresa', '   ')
  preencher('CNPJ', '12.345.678/0001-96')
  preencher('E-mail', 'email-invalido')
  salvar()
  expect(screen.getByLabelText('Nome da empresa')).toHaveFocus()
  expect(screen.getByLabelText('Nome da empresa')).toHaveAccessibleDescription(/Informe um nome/)
  expect(screen.getByLabelText('CNPJ')).toHaveAccessibleDescription(/dígitos verificadores/)
  expect(screen.getByLabelText('E-mail')).toHaveAccessibleDescription('Informe um e-mail válido.')
  expect(fetch).toHaveBeenCalledTimes(1)
})

it.each([
  [400, 'dados_invalidos', /Dados inválidos/],
  [409, 'duplicado', /CNPJ ou o e-mail já está em uso/],
  [503, 'banco_indisponivel', /banco de dados está indisponível/],
])('trata PUT %i e preserva os campos', async (status, codigo, mensagem) => {
  fetch.mockResolvedValueOnce(resposta(404, ausente)).mockResolvedValueOnce(resposta(status, { erro: { codigo } }))
  render(<MinhaEmpresa />)
  await screen.findByLabelText('Nome da empresa')
  preencherEmpresa()
  salvar()
  expect(await screen.findByRole('alert')).toHaveTextContent(mensagem)
  expect(screen.getByLabelText('Nome da empresa')).toHaveValue(' Empresa de teste ')
  expect(screen.getByLabelText('CNPJ')).toHaveValue('12.345.678/0001-95')
  expect(screen.getByLabelText('E-mail')).toHaveValue(empresa.email)
})

it('mostra falhas de consulta e permite tentar de novo sem tratar 503 ou rede como cadastro vazio', async () => {
  fetch.mockRejectedValueOnce(new TypeError('offline'))
    .mockResolvedValueOnce(resposta(503, { erro: { codigo: 'banco_indisponivel' } }))
    .mockResolvedValueOnce(resposta(200, empresa))
  render(<MinhaEmpresa />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/Falha na consulta.*conectar à API/)
  expect(screen.queryByText(/Nenhuma empresa cadastrada/)).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(/banco de dados está indisponível/)
  expect(screen.queryByRole('button', { name: 'Salvar empresa' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
  expect(await screen.findByDisplayValue(empresa.nome)).toBeInTheDocument()
})

it('trata 404 de rota ainda indisponível como erro de consulta', async () => {
  fetch.mockResolvedValueOnce(resposta(404, { erro: { codigo: 'rota_inexistente' } }))
  render(<MinhaEmpresa />)
  expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 404')
  expect(screen.queryByText(/Nenhuma empresa cadastrada/)).not.toBeInTheDocument()
})

it('rejeita uma resposta de sucesso fora do formato esperado', async () => {
  fetch.mockResolvedValueOnce(resposta(200, { nome: empresa.nome }))
  render(<MinhaEmpresa />)
  expect(await screen.findByRole('alert')).toHaveTextContent(/dados inesperados/)
})

it.each(['', 'simulado'])('informa que o cadastro exige a API no modo %j', (modo) => {
  vi.stubEnv('VITE_RADARLEAD_MODO', modo)
  render(<MinhaEmpresa />)
  expect(screen.getByText(/O cadastro real exige a API/)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Salvar empresa' })).not.toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})
