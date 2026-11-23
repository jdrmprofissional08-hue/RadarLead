import { describe, expect, it } from 'vitest'
import { validarPerfil } from '../src/utils/perfilProspeccao.js'

const entrada = {
  nome: ' Perfil de exemplo ',
  cnaes: ['6204000'],
  cnae: ' 0123-4/56 ',
  porte: '3',
  municipio: '5208707',
  pesos: { peso_cnae: '50', peso_porte: '25', peso_localizacao: '25' },
}

describe('Perfil v1.0', () => {
  it('rejeita nome em branco, CNAE ausente, porte e município vazios', () => {
    const { erros } = validarPerfil({
      ...entrada, nome: '   ', cnaes: [], cnae: '', porte: '', municipio: '',
    })
    expect(Object.keys(erros)).toEqual(['nome', 'cnae', 'porte', 'municipio'])
  })

  it('rejeita um CNAE malformado', () => {
    expect(validarPerfil({ ...entrada, cnae: '1234-5' }).erros.cnae).toBeDefined()
  })

  it('identifica duplicatas mesmo com máscara', () => {
    expect(validarPerfil({ ...entrada, cnae: '6204-0/00' }).erros.cnae)
      .toBe('Este CNAE já foi adicionado.')
  })

  it.each(['', '-1', '50.5', '101'])('rejeita peso inválido %j', (peso_cnae) => {
    const { erros } = validarPerfil({ ...entrada, pesos: { ...entrada.pesos, peso_cnae } })
    expect(erros.peso_cnae).toBeDefined()
  })

  it('rejeita soma diferente de 100', () => {
    const { erros } = validarPerfil({ ...entrada, pesos: { ...entrada.pesos, peso_cnae: '49' } })
    expect(erros.totalPesos).toBe('A soma dos pesos deve ser exatamente 100.')
  })

  it.each(['0', '2', null])('rejeita porte %j', (porte) => {
    expect(validarPerfil({ ...entrada, porte }).erros.porte).toBeDefined()
  })

  it.each(['1', '3', '5'])('produz um payload plano e tipado com porte %s', (porte) => {
    const { perfilValidado } = validarPerfil({ ...entrada, porte })
    expect(perfilValidado).toStrictEqual({
      nome: 'Perfil de exemplo',
      cnaes_desejados: ['6204000', '0123456'],
      porte_desejado: Number(porte),
      municipio_alvo_ibge: '5208707',
      peso_cnae: 50,
      peso_porte: 25,
      peso_localizacao: 25,
    })
  })
})
