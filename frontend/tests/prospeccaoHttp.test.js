import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buscarEmpresasHttp } from '../src/services/prospeccaoHttp.js'
import { obterServicoProspeccao } from '../src/services/prospeccao.js'
import { buscarEmpresasSimuladas } from '../src/services/prospeccaoSimulada.js'

const perfil = {
  nome: 'TI em Goiânia',
  cnaes_desejados: ['6204000'],
  porte_desejado: 3,
  municipio_alvo_ibge: '5208707',
  peso_cnae: 50,
  peso_porte: 25,
  peso_localizacao: 25,
}

const lead = {
  cnpj: '11111111000100',
  razao_social: 'Empresa de exemplo',
  pontuacao: 0,
  justificativas: ['CNAE diferente: +0 pontos'],
  cnae_principal: '6204000',
  porte: 3,
  porte_descricao: 'Empresa de pequeno porte',
  municipio_ibge: '5208707',
  status: 'novo',
}

function responder(status, dados) {
  fetch.mockResolvedValueOnce(new Response(JSON.stringify(dados), { status }))
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn())
  vi.stubEnv('VITE_RADARLEAD_API_URL', '')
  vi.stubEnv('VITE_RADARLEAD_MODO', '')
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('Serviço HTTP', () => {
  it('envia o objeto plano v1.0 e preserva os dados do lead, incluindo pontuação zero', async () => {
    responder(201, { leads: [{ ...lead, campoExtra: true }], total_leads: 1, total_empresas_avaliadas: 2 })
    await expect(buscarEmpresasHttp(perfil)).resolves.toStrictEqual([lead])
    expect(fetch).toHaveBeenCalledExactlyOnceWith('http://127.0.0.1:8000/api/prospeccoes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(perfil),
    })
  })

  it('aceita lista vazia e usa a URL configurada', async () => {
    vi.stubEnv('VITE_RADARLEAD_API_URL', 'http://localhost:8001/')
    responder(201, { leads: [], total_leads: 0, total_empresas_avaliadas: 2 })
    await expect(buscarEmpresasHttp(perfil)).resolves.toEqual([])
    expect(fetch.mock.calls[0][0]).toBe('http://localhost:8001/api/prospeccoes')
  })

  it.each([
    [400, 'json_invalido', 'O corpo deve ser um objeto JSON'],
    [400, 'dados_invalidos', 'Os pesos devem somar 100'],
    [404, 'nao_encontrado', 'Perfil não encontrado'],
    [404, 'rota_inexistente', 'Rota não encontrada'],
    [405, 'metodo_nao_permitido', 'Método HTTP não permitido nesta rota'],
    [500, 'erro_interno', 'Erro interno do servidor'],
    [502, 'falha_na_prospeccao', 'Falha ao executar a prospecção'],
    [503, 'banco_indisponivel', 'Banco indisponível'],
  ])('apresenta a mensagem da API para HTTP %i (%s)', async (status, codigo, mensagem) => {
    responder(status, { erro: { codigo, mensagem } })
    await expect(buscarEmpresasHttp(perfil)).rejects.toThrow(mensagem)
  })

  it('explica falhas de conexão sem tentar o simulador', async () => {
    vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
    fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    await expect(obterServicoProspeccao().buscarEmpresas(perfil)).rejects.toThrow('Não foi possível conectar à API')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('usa mensagem genérica para erro fora do formato JSON', async () => {
    fetch.mockResolvedValueOnce(new Response('<html>Indisponível</html>', { status: 503 }))
    await expect(buscarEmpresasHttp(perfil)).rejects.toThrow('HTTP 503')
  })

  it('rejeita um sucesso sem a lista de leads', async () => {
    responder(201, { total_leads: 0 })
    await expect(buscarEmpresasHttp(perfil)).rejects.toThrow('resposta de prospecção inválida')
  })

  it('aceita campos cadastrais nulos no lead', async () => {
    const incompleto = { ...lead, cnae_principal: null, porte: null, porte_descricao: null, municipio_ibge: null }
    responder(201, { leads: [incompleto] })
    await expect(buscarEmpresasHttp(perfil)).resolves.toEqual([incompleto])
  })
})

describe('Seleção da origem da busca', () => {
  it.each(['', 'simulado'])('seleciona o simulador com configuração %j', (modo) => {
    vi.stubEnv('VITE_RADARLEAD_MODO', modo)
    expect(obterServicoProspeccao()).toEqual({ modo: 'simulado', buscarEmpresas: buscarEmpresasSimuladas })
  })

  it('seleciona HTTP quando configurado', () => {
    vi.stubEnv('VITE_RADARLEAD_MODO', 'http')
    expect(obterServicoProspeccao()).toEqual({ modo: 'http', buscarEmpresas: buscarEmpresasHttp })
  })

  it('rejeita configuração inválida', async () => {
    vi.stubEnv('VITE_RADARLEAD_MODO', 'outro')
    await expect(obterServicoProspeccao().buscarEmpresas(perfil)).rejects.toThrow('Modo de prospecção inválido')
    expect(fetch).not.toHaveBeenCalled()
  })
})
