import municipios from '../data/municipios.json'

function normalizar(texto) {
  return texto.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').trim()
}

export const municipiosPorCodigo = new Map(municipios.map((m) => [m.codigo, m]))
const indice = municipios.map((municipio) => ({
  municipio,
  nome: normalizar(municipio.nome),
  uf: municipio.uf.toLowerCase(),
}))
const ordem = new Intl.Collator('pt-BR')
const ufs = new Set(indice.map(({ uf }) => uf))

export function pesquisarMunicipios(consulta) {
  const texto = normalizar(consulta)
  if (!texto) return []
  if (/^\d+$/.test(texto)) {
    const exato = municipiosPorCodigo.get(texto)
    if (exato) return [exato]
    return municipios.filter(({ codigo }) => codigo.startsWith(texto)).slice(0, 12)
  }

  const termos = texto.split(' ')
  const ufBuscada = ufs.has(termos.at(-1)) ? termos.pop() : null
  const nomeBuscado = termos.join(' ')
  return indice.filter(({ nome, uf }) =>
    (!ufBuscada || uf === ufBuscada) && termos.every((termo) => nome.includes(termo)),
  ).map(({ municipio, nome }) => ({
    municipio,
    prioridade: nome === nomeBuscado ? 0 : nome.startsWith(nomeBuscado) ? 1 : 2,
  })).sort((a, b) => a.prioridade - b.prioridade ||
    ordem.compare(a.municipio.nome, b.municipio.nome) ||
    ordem.compare(a.municipio.uf, b.municipio.uf))
    .slice(0, 12).map(({ municipio }) => municipio)
}
