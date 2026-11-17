
from src.Recomendadores.base import Recomendador


class ClassificadorPorConteudo(Recomendador):

    def __init__(self, peso_cnae=50, peso_porte=25,
                 peso_localizacao=25):

        self.peso_cnae = peso_cnae
        self.peso_porte = peso_porte
        self.peso_localizacao = peso_localizacao

    def classificar(self, empresa: dict, perfil: dict) -> dict:
        pontuacao = 0
        justificativas = []

        if empresa["cnae_principal"] in perfil["cnaes_desejados"]:
            pontuacao += self.peso_cnae
            justificativas.append(
                f"CNAE compatível: +{self.peso_cnae} pontos"
            )
        else:
            justificativas.append(
                "CNAE diferente: +0 pontos"
            )

        if empresa["porte"] == perfil["porte_desejado"]:
            pontuacao += self.peso_porte
            justificativas.append(
                f"Porte compatível: +{self.peso_porte} pontos"
            )
        else:
            justificativas.append(
                "Porte diferente: +0 pontos"
            )

        if (
            empresa["municipio_ibge"]
            == perfil["municipio_alvo_ibge"]
        ):
            pontuacao += self.peso_localizacao
            justificativas.append(
                f"Município compatível: +{self.peso_localizacao} pontos"
            )
        else:
            justificativas.append(
                "Município diferente: +0 pontos"
            )

        return {
            "pontuacao": pontuacao,
            "justificativas": justificativas
        }

    def recomendar(self, empresas: list, perfil: dict) -> list:
        resultados = []

        for empresa in empresas:
            classificacao = self.classificar(empresa, perfil)

            resultado = {
                "cnpj": empresa.get("cnpj"),
                "razao_social": empresa.get("razao_social"),
                "pontuacao": classificacao["pontuacao"],
                "justificativas": classificacao["justificativas"]
            }

            resultados.append(resultado)

        resultados.sort(
            key=lambda item: item["pontuacao"],
            reverse=True
        )

        return resultados
