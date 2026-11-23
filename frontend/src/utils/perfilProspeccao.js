import { municipiosPorCodigo } from './pesquisaMunicipio.js'

export const portesPerfil = [
  { codigo: 1, rotulo: 'Microempresa (ME)' },
  { codigo: 3, rotulo: 'Empresa de Pequeno Porte (EPP)' },
  { codigo: 5, rotulo: 'Demais empresas' },
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
  return Number.isInteger(valor) && valor >= 0 && valor <= 100 ? valor : null
}

export function totalizarPesos(pesos) {
  const valores = criterios.map(({ chave }) => converterPeso(pesos[chave]))
  if (valores.includes(null)) return null

  return valores.reduce((soma, valor) => soma + valor, 0)
}

export function validarPerfil({ nome, cnaes, cnae = '', porte, municipio, pesos }) {
  const erros = {}
  const nomeNormalizado = nome.trim()
  if (!nomeNormalizado) erros.nome = 'Informe o nome do perfil.'

  let cnaesDesejados = cnaes

  if (cnae.trim() !== '') {
    const { codigo, erro } = prepararCnae(cnae, cnaes)
    if (erro) erros.cnae = erro
    else cnaesDesejados = [...cnaes, codigo]
  } else if (cnaes.length === 0) {
    erros.cnae = 'Informe pelo menos um CNAE.'
  }

  const codigoPorte = Number(porte)
  if (!portesPerfil.some(({ codigo }) => codigo === codigoPorte)) {
    erros.porte = 'Selecione um porte empresarial.'
  }
  if (!municipiosPorCodigo.has(municipio)) {
    erros.municipio = 'Selecione um município.'
  }

  const pesosNumericos = {}
  for (const { chave } of criterios) {
    const valor = converterPeso(pesos[chave])
    if (valor === null) erros[chave] = 'Informe um número inteiro entre 0 e 100.'
    else pesosNumericos[chave] = valor
  }

  const total = totalizarPesos(pesos)
  if (total !== null && total !== 100) {
    erros.totalPesos = 'A soma dos pesos deve ser exatamente 100.'
  }

  if (Object.keys(erros).length > 0) return { erros }

  return {
    perfilValidado: {
      nome: nomeNormalizado,
      cnaes_desejados: [...cnaesDesejados],
      porte_desejado: codigoPorte,
      municipio_alvo_ibge: municipio,
      ...pesosNumericos,
    },
  }
}
