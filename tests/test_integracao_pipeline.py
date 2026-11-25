
import unittest
from pathlib import Path
from unittest.mock import Mock


RAIZ = Path(__file__).resolve().parents[1]

# Esses arquivos pertencem às branches dos colegas.
DEPENDENCIAS = [
    "src/dominio/empresa.py",
    "src/persistencia/repositorio_memoria.py",
    "src/servicos/servico_prospeccao.py",
    "src/api/recomendador_projeto.py",
    "src/Recomendadores/pipeline.py",
]

INTEGRACAO_DISPONIVEL = all(
    (RAIZ / arquivo).is_file()
    for arquivo in DEPENDENCIAS
)


@unittest.skipUnless(
    INTEGRACAO_DISPONIVEL,
    "Aguardando integracao do backend e do Machine Learning"
)
class TestIntegracaoPipeline(unittest.TestCase):

    def test_importacao_ate_geracao_de_lead(self):
        from src.integracoes.servico_empresa import (
            ServicoConsultaEmpresa
        )
        from src.integracoes.servico_importacao import (
            ServicoImportacaoEmpresas
        )
        from src.persistencia.repositorio_memoria import (
            RepositorioMemoria
        )
        from src.dominio.perfil import Perfil
        from src.servicos.servico_prospeccao import (
            ServicoProspeccao
        )
        from src.api.recomendador_projeto import (
            RecomendadorDoProjeto
        )

        cnpj_ativo = "19131243000197"
        cnpj_inativo = "22222222000191"

        # 1. Simular a BrasilAPI.
        cliente = Mock()

        def consultar_cnpj(cnpj):
            return {
                "cnpj": cnpj,
                "razao_social": (
                    "Empresa Ativa"
                    if cnpj == cnpj_ativo
                    else "Empresa Inativa"
                ),
                "cnae_fiscal": 6204000,
                "codigo_porte": 3,
                "codigo_municipio_ibge": 5205109,
                "situacao_cadastral": (
                    2 if cnpj == cnpj_ativo else 8
                ),
                "cep": "75701000",
            }

        cliente.consultar_cnpj.side_effect = consultar_cnpj

        cliente.consultar_cep.return_value = {
            "cep": "75701000",
            "city": "Catalao",
            "state": "GO",
            "ibge": {"city": "5205109"},
            "location": {
                "coordinates": {
                    "latitude": -18.16,
                    "longitude": -47.94,
                }
            },
        }

        # 2. Importar usando seu modulo.
        repositorio = RepositorioMemoria()

        consulta = ServicoConsultaEmpresa(cliente=cliente)

        importador = ServicoImportacaoEmpresas(
            consulta,
            repositorio
        )

        resultado = importador.importar_cnpjs([
            cnpj_ativo,
            cnpj_inativo,
        ])

        self.assertCountEqual(
            resultado["importados"],
            [cnpj_ativo, cnpj_inativo]
        )

        self.assertEqual(
            len(repositorio.listar_empresas()),
            2
        )

        # 3. Criar o perfil de prospeccao.
        perfil = Perfil(
            nome="Tecnologia em Catalao",
            cnaes_desejados=["6204000"],
            porte_desejado=3,
            municipio_alvo_ibge="5205109",
        )

        repositorio.salvar_perfil(perfil)

        # 4. Executar backend e Machine Learning.
        servico = ServicoProspeccao(
            repositorio,
            RecomendadorDoProjeto()
        )

        prospeccao = servico.executar(perfil.id)

        # 5. Validar a classificacao.
        self.assertEqual(
            prospeccao.total_empresas_avaliadas,
            2
        )

        self.assertEqual(
            len(prospeccao.leads),
            1
        )

        lead = prospeccao.leads[0]

        self.assertEqual(lead.cnpj, cnpj_ativo)
        self.assertEqual(lead.pontuacao, 100)

        # 6. Confirmar que a prospeccao foi salva.
        prospeccao_salva = (
            repositorio.buscar_prospeccao(
                prospeccao.id
            )
        )

        self.assertEqual(
            len(prospeccao_salva.leads),
            1
        )


if __name__ == "__main__":
    unittest.main()
