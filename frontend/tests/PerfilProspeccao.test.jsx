// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
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
  preencher('Pesquisar por atividade ou código CNAE', '6204-0/00')
  fireEvent.click(screen.getByRole('option', { name: /6204-0\/00/ }))
  preencher('Porte empresarial', '3')
  preencher('Município-alvo', '5208707')
  fireEvent.click(screen.getByRole('option', { name: /Goiânia/ }))
}

function buscar() {
  fireEvent.click(screen.getByRole('button', { name: 'Buscar empresas' }))
}

describe('Página de prospecção', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_RADARLEAD_MODO', 'simulado')
    buscarEmpresasSimuladas.mockReset()
  })

  afterEach(() => vi.unstubAllEnvs())

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
    expect(screen.getByRole('button', { name: /Remover CNAE 6204000/ })).toBeInTheDocument()
    expect(screen.getByLabelText('CNAE')).toHaveValue(49)
    expect(buscarEmpresasSimuladas).not.toHaveBeenCalled()
  })

  it('adiciona e remove CNAEs sem aceitar duplicatas normalizadas', () => {
    render(<PerfilProspeccao />)
    preencher('Pesquisar por atividade ou código CNAE', '0111-3/01')
    fireEvent.click(screen.getByRole('option', { name: /Cultivo de arroz/ }))
    preencher('Pesquisar por atividade ou código CNAE', '0111301')
    const repetida = screen.getByRole('option', { name: /Cultivo de arroz/ })
    expect(repetida).toHaveAttribute('aria-disabled', 'true')
    fireEvent.click(repetida)
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

it('descarta a resposta HTTP antiga e apresenta os dados do lead atual', async () => {
  const anterior = Promise.withResolvers()
  const atual = Promise.withResolvers()
  const fetchControlado = vi.fn().mockReturnValueOnce(anterior.promise).mockReturnValueOnce(atual.promise)
  vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
  vi.stubEnv('VITE_RADARLEAD_API_URL', 'http://127.0.0.1:8000')
  vi.stubGlobal('fetch', fetchControlado)

  try {
    render(<PerfilProspeccao />)
    expect(screen.getByText(/Busca pela API do RadarLead/)).toBeInTheDocument()
    preencherPerfil()
    buscar()
    preencher('Nome do perfil', 'Busca HTTP atual')
    buscar()
    expect(fetchControlado).toHaveBeenCalledTimes(2)

    function resposta(razao_social, municipio_ibge) {
      return new Response(JSON.stringify({ leads: [{
        cnpj: '11111111000100', razao_social, municipio_ibge,
        pontuacao: 0, justificativas: [], cnae_principal: '6204000',
        porte: 3, porte_descricao: 'Empresa de pequeno porte', status: 'novo',
      }] }), { status: 201 })
    }
    await act(async () => { atual.resolve(resposta('Resultado HTTP atual', '3304557')) })
    await act(async () => { anterior.resolve(resposta('Resultado HTTP antigo', '5208707')) })
    const cartao = screen.getByRole('article')
    expect(within(cartao).getByText('Resultado HTTP atual')).toBeInTheDocument()
    expect(within(cartao).getByText('Rio de Janeiro (RJ)')).toBeInTheDocument()
    expect(within(cartao).getByText('Empresa de pequeno porte')).toBeInTheDocument()
    expect(within(cartao).getByText('Novo')).toBeInTheDocument()
    expect(screen.queryByText('Resultado HTTP antigo')).not.toBeInTheDocument()
  } finally {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  }
})
