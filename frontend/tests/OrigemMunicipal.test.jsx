// @vitest-environment jsdom
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import FormularioPerfil from '../src/components/FormularioPerfil.jsx'

const pontos = { '5208707': [-10.123, -45.456], '5205109': [0, 0] }
const carregar = () => Promise.resolve(Response.json(pontos))
const erroDeCatalogo = /catálogo local/i
let buscar, alterar, requisitar

beforeEach(() => {
  buscar = vi.fn()
  alterar = vi.fn()
  requisitar = vi.fn(carregar)
  vi.stubGlobal('fetch', requisitar)
})
afterEach(() => vi.unstubAllGlobals())

function abrir(modo = 'http') {
  render(<FormularioPerfil modo={modo} onBuscar={buscar} onAlterar={alterar} />)
}
function digitar(rotulo, value) {
  const campo = screen.getByLabelText(rotulo)
  fireEvent.change(campo, { target: { value } })
  return campo
}
function selecionar(rotulo, valor) {
  const campo = digitar(rotulo, valor)
  fireEvent.keyDown(campo, { key: 'ArrowDown' })
  fireEvent.keyDown(campo, { key: 'Enter' })
}
function modoMunicipal() {
  fireEvent.click(screen.getByRole('radio', { name: 'Selecionar município de origem' }))
}
function preencherPerfil() {
  digitar('Nome do perfil', 'Teste')
  selecionar('Pesquisar por atividade ou código CNAE', '6204000')
  digitar('Porte empresarial', '3')
  selecionar('Município-alvo', '5208707')
}
function enviar() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
}

it('usa configuração padrão e faz busca sem catálogo ou chave origem', () => {
  abrir()
  preencherPerfil()
  enviar()
  expect(requisitar).not.toHaveBeenCalled()
  expect(buscar.mock.lastCall[0]).not.toHaveProperty('origem')
})

it('mantém o modo simulado sem opção municipal e sem fetch', () => {
  abrir('simulado')
  expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  preencherPerfil()
  enviar()
  expect(buscar).toHaveBeenCalledOnce()
  expect(buscar.mock.lastCall[0]).not.toHaveProperty('origem')
  expect(requisitar).not.toHaveBeenCalled()
})

it('mantém seletores independentes, permite trocar e limpar por controles acessíveis', async () => {
  abrir()
  preencherPerfil()
  modoMunicipal()
  expect(requisitar).toHaveBeenCalledExactlyOnceWith('/dados-locais/coordenadas-municipios.json')
  const origem = await screen.findByRole('combobox', { name: 'Município de origem' })
  const alvo = screen.getByRole('combobox', { name: 'Município-alvo' })
  expect(origem.id).not.toBe(alvo.id)
  selecionar('Município de origem', '5205109')
  enviar()
  expect(buscar.mock.lastCall[0]).toMatchObject({
    municipio_alvo_ibge: '5208707', origem: { latitude: 0, longitude: 0 },
  })
  expect(buscar.mock.lastCall[0].origem).not.toHaveProperty('raio_km')
  selecionar('Município de origem', '5208707')
  fireEvent.click(screen.getByRole('checkbox', { name: 'Usar raio padrão do servidor' }))
  digitar('Raio (km)', '25,5')
  enviar()
  expect(buscar.mock.lastCall[0].origem).toStrictEqual({ latitude: -10.123, longitude: -45.456, raio_km: 25.5 })
  fireEvent.click(screen.getByRole('button', { name: /Remover município de origem Goiânia/ }))
  expect(origem).toHaveFocus()
  enviar()
  expect(buscar).toHaveBeenCalledTimes(2)
  expect(origem).toHaveAccessibleDescription(/Selecione um município de origem/)
  expect(screen.getByRole('button', { name: /^Remover município Goiânia/ })).toBeInTheDocument()
})

it('informa código ausente e bloqueia o envio municipal', async () => {
  abrir()
  preencherPerfil()
  modoMunicipal()
  const origem = await screen.findByLabelText('Município de origem')
  selecionar('Município de origem', '3170206')
  enviar()
  expect(buscar).not.toHaveBeenCalled()
  expect(origem).toHaveFocus()
  expect(origem).toHaveAccessibleDescription(/não tem coordenadas/)
})

it.each([
  ['404', () => new Response(null, { status: 404 }), /não encontrado/],
  ['rede', () => Promise.reject(new TypeError('falha')), /Falha ao carregar/],
  ['JSON malformado', () => new Response('{'), /inválido/],
  ['estrutura incompatível', () => Response.json([]), /inválido/],
  ['coordenadas inválidas', () => Response.json({ '5208707': [91, 0] }), /inválido/],
])('trata %s e permite nova tentativa', async (_, falhar, mensagem) => {
  requisitar.mockImplementationOnce(falhar)
  abrir()
  preencherPerfil()
  modoMunicipal()
  expect(await screen.findByRole('alert')).toHaveTextContent(mensagem)
  enviar()
  expect(buscar).not.toHaveBeenCalled()
  expect(screen.getByRole('radio', { name: 'Selecionar município de origem' })).toHaveFocus()
  fireEvent.click(screen.getByRole('button', { name: 'Tentar carregar novamente' }))
  await screen.findByLabelText('Município de origem')
  expect(requisitar).toHaveBeenCalledTimes(2)
})

it('descarta exibição atrasada e reutiliza o catálogo ao voltar à opção municipal', async () => {
  const pendente = Promise.withResolvers()
  requisitar.mockReturnValueOnce(pendente.promise)
  abrir()
  preencherPerfil()
  modoMunicipal()
  expect(screen.getByText(/Carregando catálogo local/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('radio', { name: 'Informar coordenadas manualmente' }))
  digitar('Latitude', '1')
  digitar('Longitude', '-2')
  await act(async () => pendente.resolve(Response.json(pontos)))
  expect(screen.queryByLabelText('Município de origem')).not.toBeInTheDocument()
  enviar()
  expect(buscar.mock.lastCall[0].origem).toStrictEqual({ latitude: 1, longitude: -2 })
  modoMunicipal()
  await screen.findByLabelText('Município de origem')
  expect(requisitar).toHaveBeenCalledOnce()
  fireEvent.click(screen.getByRole('radio', { name: 'Usar configuração do servidor' }))
  enviar()
  expect(buscar.mock.lastCall[0]).not.toHaveProperty('origem')
  expect(alterar).toHaveBeenCalled()
})
