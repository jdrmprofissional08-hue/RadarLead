// Recorte provisório: códigos de porte observados nos exemplos do classificador.
export const portesProvisorios = [3, 5]

// Recorte provisório de municípios com códigos da tabela oficial do IBGE.
export const municipiosProvisorios = [
  { nome: 'Goiânia', uf: 'GO', codigo: '5208707' },
  { nome: 'São Paulo', uf: 'SP', codigo: '3550308' },
]

export const criterios = [
  { chave: 'peso_cnae', rotulo: 'CNAE', inicial: '50' },
  { chave: 'peso_porte', rotulo: 'Porte', inicial: '25' },
  { chave: 'peso_localizacao', rotulo: 'Localização', inicial: '25' },
]

export function prepararCnae(entrada, cnaes) {
  const valor = entrada.trim()
  if (!/^(?:[0-9]{7}|[0-9]{4}-[0-9]\/[0-9]{2})$/.test(valor)) {
    return { erro: 'Informe sete dígitos ou use o formato 6204-0/00.' }
  }

  const codigo = valor.replace(/[-/]/g, '')
  if (cnaes.includes(codigo)) {
    return { erro: 'Este CNAE já foi adicionado.' }
  }

  return { codigo }
}

function converterPeso(entrada) {
  if (entrada.trim() === '') return null

  const valor = Number(entrada)
  return Number.isFinite(valor) && valor >= 0 ? valor : null
}

export function totalizarPesos(pesos) {
  const valores = criterios.map(({ chave }) => converterPeso(pesos[chave]))
  if (valores.includes(null)) return null

  const total = valores.reduce((soma, valor) => soma + valor, 0)
  return Number.isFinite(total) ? total : null
}

export function validarPerfil({ cnaes, cnae, porte, municipio, pesos }) {
  const erros = {}
  let cnaesDesejados = cnaes

  if (cnae.trim() !== '') {
    const { codigo, erro } = prepararCnae(cnae, cnaes)
    if (erro) erros.cnae = erro
    else cnaesDesejados = [...cnaes, codigo]
  } else if (cnaes.length === 0) {
    erros.cnae = 'Informe pelo menos um CNAE.'
  }

  const codigoPorte = Number(porte)
  if (!portesProvisorios.includes(codigoPorte)) {
    erros.porte = 'Selecione um porte empresarial.'
  }
  if (!municipiosProvisorios.some(({ codigo }) => codigo === municipio)) {
    erros.municipio = 'Selecione um município.'
  }

  const pesosNumericos = {}
  for (const { chave } of criterios) {
    const valor = converterPeso(pesos[chave])
    if (valor === null) erros[chave] = 'Informe um número maior ou igual a zero.'
    else pesosNumericos[chave] = valor
  }

  if (Object.keys(erros).length > 0) return { erros }

  return {
    perfilValidado: {
      perfil: {
        cnaes_desejados: [...cnaesDesejados],
        porte_desejado: codigoPorte,
        municipio_alvo_ibge: municipio,
      },
      pesos: pesosNumericos,
    },
  }
}
