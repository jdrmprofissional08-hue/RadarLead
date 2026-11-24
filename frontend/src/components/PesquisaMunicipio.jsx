import CampoPesquisa from './CampoPesquisa.jsx'
import { municipiosPorCodigo, pesquisarMunicipios } from '../utils/pesquisaMunicipio.js'

export default function PesquisaMunicipio({ atributos, codigo, estiloCampo, onAlterar, rotulo = 'Município-alvo',
  rotuloLista = 'Sugestões de municípios', rotuloRemocao = 'município' }) {
  const selecionado = municipiosPorCodigo.get(codigo)
  return (
    <CampoPesquisa
      atributos={atributos}
      estiloCampo={estiloCampo}
      rotulo={rotulo}
      ajuda="Pesquise por nome, UF ou código IBGE. Use as setas e Enter para selecionar ou Escape para fechar."
      rotuloLista={rotuloLista}
      semResultados="Nenhum município encontrado."
      pesquisar={pesquisarMunicipios}
      renderizarOpcao={({ nome, uf, codigo: ibge }) => <><strong>{nome} ({uf})</strong><span>{ibge}</span></>}
      onSelecionar={onAlterar}
    >
      {selecionado && (
        <button
          type="button"
          aria-label={`Remover ${rotuloRemocao} ${selecionado.nome} (${selecionado.uf})`}
          onClick={() => {
            document.getElementById(atributos.id)?.focus()
            onAlterar('')
          }}
          className="mt-3 min-h-11 max-w-full rounded-lg bg-fundo px-3 py-2 text-left text-sm text-texto hover:bg-acao-suave hover:text-acao"
        >
          {selecionado.nome} ({selecionado.uf}) <span aria-hidden="true">×</span>
        </button>
      )}
    </CampoPesquisa>
  )
}
