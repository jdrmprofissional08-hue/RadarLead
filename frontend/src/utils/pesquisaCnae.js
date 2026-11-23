import catalogo from '../data/cnaes.json'

function normalizarTexto(valor) {
  return valor.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim()
}

const indice = catalogo.map((atividade) => ({
  atividade, texto: normalizarTexto(atividade.descricao),
}))
export const cnaesPorCodigo = new Map(catalogo.map((atividade) => [atividade.codigo, atividade]))

export function formatarCnae(codigo) {
  return codigo.replace(/^(\d{4})(\d)(\d{2})$/, '$1-$2/$3')
}

export function pesquisarCnaes(consulta) {
  const texto = normalizarTexto(consulta)
  if (!texto) return []

  if (/^[0-9][0-9./\s-]*$/.test(texto)) {
    const codigo = texto.replace(/\D/g, '')
    const exato = cnaesPorCodigo.get(codigo)
    if (exato) return [exato]
    return catalogo.filter((atividade) => atividade.codigo.startsWith(codigo)).slice(0, 12)
  }

  const termos = texto.split(/\s+/)
  return indice.filter((item) => termos.every((termo) => item.texto.includes(termo)))
    .slice(0, 12).map(({ atividade }) => atividade)
}
