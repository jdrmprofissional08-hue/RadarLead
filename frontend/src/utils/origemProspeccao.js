export const origemInicial = {
  modo: 'servidor',
  municipioOrigem: '',
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

function latitudeValida(valor) {
  return Number.isFinite(valor) && valor >= -90 && valor <= 90
}

function longitudeValida(valor) {
  return Number.isFinite(valor) && valor >= -180 && valor <= 180
}

export function coordenadasValidas(par) {
  return Array.isArray(par) && par.length === 2 &&
    latitudeValida(par[0]) && longitudeValida(par[1])
}

export function validarOrigem(configuracao, catalogo) {
  if (configuracao.modo === 'servidor') return { erros: {} }

  const municipal = configuracao.modo === 'municipio'
  const ponto = catalogo?.[configuracao.municipioOrigem]
  const pontoValido = coordenadasValidas(ponto)
  const [latitude, longitude] = municipal
    ? (pontoValido ? ponto : [])
    : [lerDecimal(configuracao.latitude), lerDecimal(configuracao.longitude)]
  const erros = {}
  const origem = { latitude, longitude }

  if (municipal && !pontoValido) {
    erros.municipioOrigem = !catalogo
      ? 'O catálogo local precisa estar disponível para usar a origem municipal.'
      : configuracao.municipioOrigem
        ? 'O município selecionado não tem coordenadas disponíveis.'
        : 'Selecione um município de origem.'
  }
  if (!municipal && !latitudeValida(latitude)) {
    erros.latitude = 'Informe uma latitude decimal entre -90 e 90.'
  }
  if (!municipal && !longitudeValida(longitude)) {
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
