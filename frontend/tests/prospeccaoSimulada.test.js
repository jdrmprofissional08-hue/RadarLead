import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { buscarEmpresasSimuladas } from '../src/services/prospeccaoSimulada.js'

const perfil = {
  nome: 'Perfil de exemplo',
  cnaes_desejados: ['6204000'],
  porte_desejado: 3,
  municipio_alvo_ibge: '5208707',
  peso_cnae: 40,
  peso_porte: 35,
  peso_localizacao: 25,
}

describe('Busca simulada', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  async function buscar(filtros) {
    const busca = buscarEmpresasSimuladas(filtros)
    await vi.runAllTimersAsync()
    return busca
  }

  it('filtra pelo CNAE e soma os pesos dos critérios compatíveis', async () => {
    const resultados = await buscar(perfil)
    expect(resultados.map(({ razao_social, pontuacao }) => [razao_social, pontuacao]))
      .toEqual([
        ['Empresa Exemplo Beta', 40],
        ['Empresa Exemplo Gama', 100],
        ['Empresa Exemplo Delta', 40],
      ])
    expect(resultados[0].justificativas).toEqual([
      'CNAE compatível: +40 pontos', 'Porte diferente: +0 pontos', 'Município diferente: +0 pontos',
    ])
    expect(resultados[1].justificativas).toEqual([
      'CNAE compatível: +40 pontos', 'Porte compatível: +35 pontos', 'Município compatível: +25 pontos',
    ])
  })

  it('retorna vazio para um CNAE ausente na base', async () => {
    expect(await buscar({ ...perfil, cnaes_desejados: ['0123456'] })).toEqual([])
  })

  it('omite correspondências com zero pontos apenas na simulação', async () => {
    const resultados = await buscar({ ...perfil, peso_cnae: 0, peso_porte: 75 })
    expect(resultados.map(({ razao_social, pontuacao }) => [razao_social, pontuacao]))
      .toEqual([['Empresa Exemplo Gama', 100]])
  })
})
