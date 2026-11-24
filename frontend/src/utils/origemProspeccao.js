export const origemInicial = {
  modo: 'servidor',
  latitude: '',
  longitude: '',
  raioPadrao: true,
  raio: '',
}

function lerDecimal(entrada) {
  const texto = entrada.trim()
  if (!/^[+-]?[0-9]+(?:[.,][0-9]+)?$/.test(texto)) return null

  const valor = Number(texto.replace(',', '.'))
  return Number.isFinite(valor) ? valor : null
}

export function validarOrigem(configuracao) {
  if (configuracao.modo === 'servidor') return { erros: {} }

  const latitude = lerDecimal(configuracao.latitude)
  const longitude = lerDecimal(configuracao.longitude)
  const erros = {}
  const origem = { latitude, longitude }

  if (latitude === null || latitude < -90 || latitude > 90) {
    erros.latitude = 'Informe uma latitude decimal entre -90 e 90.'
  }
  if (longitude === null || longitude < -180 || longitude > 180) {
    erros.longitude = 'Informe uma longitude decimal entre -180 e 180.'
  }
  if (!configuracao.raioPadrao) {
    const raio = lerDecimal(configuracao.raio)
    if (raio === null || raio <= 0 || raio > 350) {
      erros.raio = 'Informe um raio decimal maior que zero e de até 350 km.'
    } else {
      origem.raio_km = raio
    }
  }

  return Object.keys(erros).length ? { erros } : { erros, origem }
}
