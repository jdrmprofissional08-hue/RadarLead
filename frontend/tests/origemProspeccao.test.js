import { expect, it } from 'vitest'
import { origemInicial, validarOrigem } from '../src/utils/origemProspeccao.js'

const manual = { ...origemInicial, modo: 'manual', latitude: '0', longitude: '0' }

it('não tem coordenadas fixas e ignora todos os campos no modo servidor', () => {
  expect(origemInicial.latitude).toBe('')
  expect(origemInicial.longitude).toBe('')
  expect(validarOrigem({ ...manual, modo: 'servidor', latitude: 'inválida', raioPadrao: false })).toEqual({ erros: {} })
})

it.each([
  ['0', '0', 0, 0],
  ['  -18,1656 ', ' -47.944 ', -18.1656, -47.944],
  ['90', '180', 90, 180],
  ['-90', '-180', -90, -180],
])('aceita coordenadas %s e %s e omite raio inativo', (latitude, longitude, lat, lon) => {
  const resultado = validarOrigem({ ...manual, latitude, longitude, raio: 'inválido' })
  expect(resultado).toStrictEqual({ erros: {}, origem: { latitude: lat, longitude: lon } })
  expect(Object.hasOwn(resultado.origem, 'raio_km')).toBe(false)
})

it.each(['', '   ', 'NaN', 'Infinity', '12abc', '1.000,5', '1,000.5', '1 000', '0x10', '1e1', '90.0001', '-90.0001', '9'.repeat(400)])(
  'rejeita latitude inválida %j', (latitude) => {
    const resultado = validarOrigem({ ...manual, latitude })
    expect(resultado.erros.latitude).toBeDefined()
    expect(Object.hasOwn(resultado, 'origem')).toBe(false)
  },
)

it.each(['180.0001', '-180,0001', ''])('rejeita longitude inválida %j', (longitude) => {
  expect(validarOrigem({ ...manual, longitude }).erros.longitude).toBeDefined()
})

it.each([['0,25', 0.25], ['350', 350]])('aceita raio personalizado %s', (raio, esperado) => {
  expect(validarOrigem({ ...manual, raioPadrao: false, raio }).origem.raio_km).toBe(esperado)
})

it.each(['0', '-1', '350.0001', '', '   ', '1,2,3'])('rejeita raio personalizado %j', (raio) => {
  expect(validarOrigem({ ...manual, raioPadrao: false, raio }).erros.raio).toBeDefined()
})
