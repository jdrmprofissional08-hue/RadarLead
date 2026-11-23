import ResultadoEmpresa from './ResultadoEmpresa.jsx'

function pontuacaoParaOrdenar({ pontuacao }) {
  return Number.isFinite(pontuacao) ? pontuacao : -Infinity
}

export default function ListaResultados({ resultados }) {
  if (resultados.length === 0) {
    return <p className="mt-4 rounded-xl border border-divisor bg-superficie px-5 py-8 text-center text-suave">Nenhuma empresa encontrada</p>
  }

  const ordenados = [...resultados].sort(
    (a, b) => pontuacaoParaOrdenar(b) - pontuacaoParaOrdenar(a),
  )

  return (
    <ol className="mt-4 space-y-3">
      {ordenados.map((empresa) => (
        <li key={empresa.cnpj || empresa.id}>
          <ResultadoEmpresa empresa={empresa} />
        </li>
      ))}
    </ol>
  )
}
