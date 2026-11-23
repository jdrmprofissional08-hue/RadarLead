// @vitest-environment jsdom
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import PerfilProspeccao from '../src/pages/PerfilProspeccao.jsx'
import { pesquisarCnaes, cnaesPorCodigo } from '../src/utils/pesquisaCnae.js'
import { buscarEmpresasSimuladas } from '../src/services/prospeccaoSimulada.js'

vi.mock('../src/services/prospeccaoSimulada.js', () => ({
  buscarEmpresasSimuladas: vi.fn(),
}))

beforeEach(() => {
  vi.stubEnv('VITE_RADARLEAD_MODO', 'simulado')
  buscarEmpresasSimuladas.mockReset()
})

afterEach(() => vi.unstubAllEnvs())

it('localiza descrições por termos sem acentos ou distinção de caixa', () => {
  expect(pesquisarCnaes('INFORMACAO consultoria')).toEqual(pesquisarCnaes('informação consultoria'))
  expect(pesquisarCnaes('INFORMACAO consultoria').map(({ codigo }) => codigo)).toContain('6204000')
})

it('pesquisa por prefixo e por código exato com ou sem máscara', () => {
  expect(cnaesPorCodigo.size).toBe(1332)
  expect(pesquisarCnaes('0111-3/01')).toEqual([{ codigo: '0111301', descricao: 'Cultivo de arroz' }])
  expect(pesquisarCnaes('0111301')).toEqual(pesquisarCnaes('0111-3/01'))
  expect(pesquisarCnaes('0111').map(({ codigo }) => codigo)).toContain('0111301')
})

it('seleciona múltiplas atividades por teclado e clique, sem seleção automática', () => {
  render(<PerfilProspeccao />)
  const campo = screen.getByRole('combobox', { name: /Pesquisar por atividade/ })
  fireEvent.change(campo, { target: { value: 'arroz' } })
  fireEvent.keyDown(campo, { key: 'Enter' })
  expect(screen.queryByRole('list', { name: 'CNAEs adicionados' })).not.toBeInTheDocument()
  fireEvent.keyDown(campo, { key: 'Escape' })
  expect(campo).toHaveAttribute('aria-expanded', 'false')
  fireEvent.change(campo, { target: { value: '0111301' } })
  fireEvent.keyDown(campo, { key: 'ArrowUp' })
  expect(within(screen.getByRole('listbox')).getByRole('option')).toHaveAttribute('aria-selected', 'true')
  fireEvent.keyDown(campo, { key: 'Enter' })
  fireEvent.change(campo, { target: { value: '6204000' } })
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option'))
  expect(screen.getByRole('button', { name: /Remover CNAE 0111301/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Remover CNAE 6204000/ })).toBeInTheDocument()
})

it('mostra ausência de correspondência e exige selecionar uma atividade', () => {
  render(<PerfilProspeccao />)
  const campo = screen.getByRole('combobox', { name: /Pesquisar por atividade/ })
  fireEvent.change(campo, { target: { value: 'ZZZZZZ' } })
  expect(screen.getByText('Nenhuma atividade encontrada.')).toBeInTheDocument()
  fireEvent.change(campo, { target: { value: '6204000' } })
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
  expect(screen.getByText('Informe pelo menos um CNAE.')).toBeInTheDocument()
})

it('invalida resultados quando uma atividade é removida', async () => {
  buscarEmpresasSimuladas.mockResolvedValueOnce([{ id: 'demo', razao_social: 'Empresa teste', pontuacao: 100 }])
  render(<PerfilProspeccao />)
  for (const [rotulo, value] of [
    ['Nome do perfil', 'Exemplo'], ['Porte empresarial', '3'], ['Município-alvo', '5208707'],
    ['Pesquisar por atividade ou código CNAE', '6204000'],
  ]) fireEvent.change(screen.getByLabelText(rotulo), { target: { value } })
  fireEvent.click(within(screen.getByRole('listbox', { name: 'Sugestões de CNAE' })).getByRole('option'))
  fireEvent.click(screen.getByRole('option', { name: /Goiânia/ }))
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
  expect(await screen.findByText('Empresa teste')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: /Remover CNAE 6204000/ }))
  expect(screen.queryByText('Empresa teste')).not.toBeInTheDocument()
})
