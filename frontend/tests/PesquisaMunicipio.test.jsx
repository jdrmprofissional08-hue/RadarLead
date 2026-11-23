// @vitest-environment jsdom
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import PerfilProspeccao from '../src/pages/PerfilProspeccao.jsx'
import { municipiosPorCodigo, pesquisarMunicipios } from '../src/utils/pesquisaMunicipio.js'
import { buscarEmpresasSimuladas } from '../src/services/prospeccaoSimulada.js'

vi.mock('../src/services/prospeccaoSimulada.js', () => ({
  buscarEmpresasSimuladas: vi.fn(),
}))

beforeEach(() => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'simulado')
  buscarEmpresasSimuladas.mockReset()
})
afterEach(() => vi.unstubAllEnvs())

function preencher(rotulo, value) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value } })
}
function escolherMunicipio(consulta, nome) {
  preencher('Município-alvo', consulta)
  fireEvent.click(within(screen.getByRole('listbox', { name: 'Sugestões de municípios' }))
    .getByRole('option', { name: nome }))
}
function buscar() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
}

it('pesquisa nome exato, sem distinção de acento ou caixa', () => {
  expect(municipiosPorCodigo.size).toBe(5571)
  expect(pesquisarMunicipios('GOIANIA')).toEqual(pesquisarMunicipios('Goiânia'))
  expect(pesquisarMunicipios('GOIANIA')[0]).toEqual({ codigo: '5208707', nome: 'Goiânia', uf: 'GO' })
})

it('pesquisa por UF e distingue municípios homônimos', () => {
  expect(pesquisarMunicipios('DF').map(({ uf }) => uf)).toEqual(['DF'])
  const homonimos = pesquisarMunicipios('Bom Jesus').filter(({ nome }) => nome === 'Bom Jesus')
  expect(homonimos.map(({ uf }) => uf)).toEqual(expect.arrayContaining(['PI', 'RS', 'SC']))
  expect(pesquisarMunicipios('Bom Jesus PI')[0]).toMatchObject({ nome: 'Bom Jesus', uf: 'PI' })
})

it('pesquisa por código IBGE e prefixo', () => {
  expect(pesquisarMunicipios('3304557')).toEqual([{ codigo: '3304557', nome: 'Rio de Janeiro', uf: 'RJ' }])
  expect(pesquisarMunicipios('520870')[0].codigo).toBe('5208707')
})

it('seleciona explicitamente por teclado e substitui ou remove a seleção única', () => {
  render(<PerfilProspeccao />)
  const campo = screen.getByRole('combobox', { name: 'Município-alvo' })
  preencher('Município-alvo', 'Goiania')
  fireEvent.keyDown(campo, { key: 'Enter' })
  expect(screen.queryByRole('button', { name: /Remover município/ })).not.toBeInTheDocument()
  fireEvent.keyDown(campo, { key: 'Escape' })
  expect(campo).toHaveAttribute('aria-expanded', 'false')
  fireEvent.keyDown(campo, { key: 'ArrowDown' })
  fireEvent.keyDown(campo, { key: 'Enter' })
  expect(screen.getByRole('button', { name: 'Remover município Goiânia (GO)' })).toBeInTheDocument()
  escolherMunicipio('3304557', /Rio de Janeiro/)
  expect(screen.getAllByRole('button', { name: /Remover município/ })).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Remover município Rio de Janeiro (RJ)' }))
  expect(campo).toHaveFocus()
  expect(screen.queryByRole('button', { name: /Remover município/ })).not.toBeInTheDocument()
})

it('exibe o estado vazio e mantém a validação quando não há seleção', () => {
  render(<PerfilProspeccao />)
  preencher('Município-alvo', 'zzzzzz')
  expect(screen.getByText('Nenhum município encontrado.')).toBeInTheDocument()
  buscar()
  expect(screen.getByText('Selecione um município.')).toBeInTheDocument()
  expect(buscarEmpresasSimuladas).not.toHaveBeenCalled()
})

it('usa o código de sete dígitos no perfil e invalida resultados ao substituir o município', async () => {
  buscarEmpresasSimuladas.mockResolvedValueOnce([{ id: 'teste', razao_social: 'Empresa teste', pontuacao: 100 }])
  render(<PerfilProspeccao />)
  preencher('Nome do perfil', 'Exemplo')
  preencher('Porte empresarial', '3')
  preencher('Pesquisar por atividade ou código CNAE', '6204000')
  fireEvent.click(screen.getByRole('option', { name: /6204-0/ }))
  escolherMunicipio('3304557', /Rio de Janeiro/)
  buscar()
  expect(buscarEmpresasSimuladas).toHaveBeenCalledWith(expect.objectContaining({ municipio_alvo_ibge: '3304557' }))
  expect(await screen.findByText('Empresa teste')).toBeInTheDocument()
  escolherMunicipio('Catalão', /Catalão/)
  expect(screen.queryByText('Empresa teste')).not.toBeInTheDocument()
})
