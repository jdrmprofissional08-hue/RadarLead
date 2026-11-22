// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PerfilProspeccao from '../src/pages/PerfilProspeccao.jsx'
import { buscarEmpresasSimuladas } from '../src/services/prospeccaoSimulada.js'

vi.mock('../src/services/prospeccaoSimulada.js', () => ({
  buscarEmpresasSimuladas: vi.fn(),
}))

function preencher(rotulo, valor) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value: valor } })
}

function preencherPerfil() {
  preencher('Nome do perfil', ' Meu perfil ')
  preencher('Código CNAE', '6204-0/00')
  preencher('Porte empresarial', '3')
  preencher('Município-alvo', '5208707')
}

function buscar() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
}

describe('Página de prospecção', () => {
  beforeEach(() => buscarEmpresasSimuladas.mockReset())

  it('exibe erros obrigatórios, foca o primeiro campo e impede a busca', () => {
    render(<PerfilProspeccao />)
    buscar()
    const nome = screen.getByLabelText('Nome do perfil')
    expect(nome).toHaveFocus()
    expect(nome).toHaveAccessibleDescription('Informe o nome do perfil.')
    expect(screen.getByText('Informe pelo menos um CNAE.')).toBeInTheDocument()
    expect(screen.getByText('Selecione um porte empresarial.')).toBeInTheDocument()
    expect(screen.getByText('Selecione um município.')).toBeInTheDocument()
    expect(buscarEmpresasSimuladas).not.toHaveBeenCalled()
  })

  it('rejeita peso fracionário e soma incorreta mantendo os valores digitados', () => {
    render(<PerfilProspeccao />)
    preencherPerfil()
    preencher('CNAE', '49.5')
    buscar()
    expect(screen.getByLabelText('CNAE')).toHaveAccessibleDescription('Informe um número inteiro entre 0 e 100.')
    preencher('CNAE', '49')
    buscar()
    expect(screen.getByLabelText('CNAE')).toHaveAccessibleDescription('A soma dos pesos deve ser exatamente 100.')
    expect(screen.getByLabelText('Código CNAE')).toHaveValue('6204-0/00')
    expect(screen.getByLabelText('CNAE')).toHaveValue(49)
    expect(buscarEmpresasSimuladas).not.toHaveBeenCalled()
  })

  it('adiciona e remove CNAEs sem aceitar duplicatas normalizadas', () => {
    render(<PerfilProspeccao />)
    const adicionar = screen.getByRole('button', { name: 'Adicionar CNAE' })
    preencher('Código CNAE', '0123-4/56')
    fireEvent.click(adicionar)
    preencher('Código CNAE', '0123456')
    fireEvent.click(adicionar)
    expect(screen.getByText('Este CNAE já foi adicionado.')).toBeInTheDocument()
    const lista = screen.getByRole('list', { name: 'CNAEs adicionados' })
    const botoes = within(lista).getAllByRole('button')
    expect(botoes).toHaveLength(1)
    fireEvent.click(botoes[0])
    expect(lista).not.toBeInTheDocument()
  })

  it('mostra carregamento, envia o payload canônico e exibe resultados após o formulário', async () => {
    const resposta = Promise.withResolvers()
    buscarEmpresasSimuladas.mockReturnValueOnce(resposta.promise)
    render(<PerfilProspeccao />)
    expect(screen.queryByRole('region', { name: 'Resultados da busca' })).not.toBeInTheDocument()
    expect(screen.getByText('Dados simulados. A busca usa uma base fictícia.')).toBeInTheDocument()
    preencherPerfil()
    buscar()
    expect(screen.getByText('Buscando empresas…')).toBeInTheDocument()
    const botao = screen.getByRole('button', { name: 'Buscar empresas' })
    expect(botao).toBeDisabled()
    expect(buscarEmpresasSimuladas).toHaveBeenCalledExactlyOnceWith({
      nome: 'Meu perfil', cnaes_desejados: ['6204000'], porte_desejado: 3,
      municipio_alvo_ibge: '5208707', peso_cnae: 50, peso_porte: 25, peso_localizacao: 25,
    })

    await act(async () => {
      resposta.resolve([{ id: 'demo', razao_social: 'Empresa Exemplo', pontuacao: 100 }])
    })
    const resultados = screen.getByRole('region', { name: 'Resultados da busca' })
    expect(within(resultados).getByText('Empresa Exemplo')).toBeInTheDocument()
    expect(botao.closest('form').compareDocumentPosition(resultados) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
    expect(botao).toBeEnabled()
    preencher('Nome do perfil', 'Outro perfil')
    expect(resultados).not.toBeInTheDocument()
  })

  it('mostra uma falha, preserva os campos e permite repetir a busca', async () => {
    buscarEmpresasSimuladas.mockRejectedValueOnce(new Error('Falha de teste')).mockResolvedValueOnce([])
    render(<PerfilProspeccao />)
    preencherPerfil()
    buscar()
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível concluir a busca simulada.')
    expect(screen.getByLabelText('Nome do perfil')).toHaveValue(' Meu perfil ')
    buscar()
    const resultados = await screen.findByRole('region', { name: 'Resultados da busca' })
    expect(within(resultados).getByText('Nenhuma empresa encontrada')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(buscarEmpresasSimuladas).toHaveBeenCalledTimes(2)
  })

  it('descarta a resposta anterior após uma busca mais recente', async () => {
    const anterior = Promise.withResolvers()
    const atual = Promise.withResolvers()
    buscarEmpresasSimuladas.mockReturnValueOnce(anterior.promise).mockReturnValueOnce(atual.promise)
    render(<PerfilProspeccao />)
    preencherPerfil()
    buscar()
    preencher('Nome do perfil', 'Busca atual')
    buscar()

    await act(async () => {
      atual.resolve([{ id: 'atual', razao_social: 'Resultado atual', pontuacao: 90 }])
    })
    await act(async () => {
      anterior.resolve([{ id: 'anterior', razao_social: 'Resultado anterior', pontuacao: 100 }])
    })
    expect(screen.getByText('Resultado atual')).toBeInTheDocument()
    expect(screen.queryByText('Resultado anterior')).not.toBeInTheDocument()
  })
})
