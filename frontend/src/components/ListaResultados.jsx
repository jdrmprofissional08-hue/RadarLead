import ResultadoEmpresa from './ResultadoEmpresa.jsx'

function pontuacaoParaOrdenar({ pontuacao }) {
  return Number.isFinite(pontuacao) ? pontuacao : -Infinity
}

export default function ListaResultados({ resultados }) {
  if (resultados.length === 0) {
    return <p className="mt-8 text-slate-300">Nenhuma empresa encontrada</p>
  }

  const ordenados = [...resultados].sort(
    (a, b) => pontuacaoParaOrdenar(b) - pontuacaoParaOrdenar(a),
  )

  return (
    <ol className="mt-8 space-y-4">
      {ordenados.map((empresa) => (
        <li key={empresa.cnpj || empresa.id}>
          <ResultadoEmpresa empresa={empresa} />
        </li>
      ))}
    </ol>
  )
}
