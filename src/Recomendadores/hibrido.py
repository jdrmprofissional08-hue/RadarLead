
import math

from src.Recomendadores.base import Recomendador
from src.Recomendadores.classificador import ClassificadorPorConteudo
from src.Recomendadores.similaridade import RecomendadorKNN


class RecomendadorHibrido(Recomendador):
    """Combina classificação por conteúdo e KNN."""

    def __init__(self, historico=None, k=3, peso_conteudo=0.7):
        if (
            isinstance(peso_conteudo, bool)
            or not isinstance(peso_conteudo, (int, float))
            or not math.isfinite(peso_conteudo)
            or not 0 <= peso_conteudo <= 1
        ):
            raise ValueError(
                "peso_conteudo deve estar entre 0 e 1"
            )

        self.peso_conteudo = float(peso_conteudo)
        self.knn = RecomendadorKNN(historico=historico, k=k)

    def treinar(self, historico):
        self.knn.treinar(historico)

    @staticmethod
    def _validar_perfil(perfil):
        if not isinstance(perfil, dict):
            raise ValueError("Perfil deve ser um dicionário")

        campos = (
            ("peso_cnae", 50),
            ("peso_porte", 25),
            ("peso_localizacao", 25)
        )

        pesos = [
            perfil.get(nome, padrao)
            for nome, padrao in campos
        ]

        if (
            any(
                type(p) is not int or not 0 <= p <= 100
                for p in pesos
            )
            or sum(pesos) != 100
        ):
            raise ValueError(
                "Pesos devem ser inteiros entre 0 e 100 e somar 100"
            )

        cnaes = perfil.get("cnaes_desejados")

        if not isinstance(cnaes, list) or not cnaes:
            raise ValueError(
                "Informe ao menos um CNAE desejado"
            )

        if type(perfil.get("porte_desejado")) is not int:
            raise ValueError("Porte desejado inválido")

        if not isinstance(
            perfil.get("municipio_alvo_ibge"), str
        ):
            raise ValueError("Município-alvo inválido")

        return pesos

    def recomendar(self, empresas: list, perfil: dict) -> list:
        if not isinstance(empresas, list):
            raise ValueError("Empresas deve ser uma lista")

        pesos = self._validar_perfil(perfil)

        if not empresas:
            return []

        # Padroniza os dados sem modificar a lista original
        empresas_normalizadas = []

        for empresa in empresas:
            normalizada = self.knn._preparar_empresa(empresa)
            normalizada["porte"] = int(normalizada["porte"])
            empresas_normalizadas.append(normalizada)

        perfil_normalizado = dict(perfil)

        perfil_normalizado["cnaes_desejados"] = [
            self.knn._codigo(c, 7, "CNAE")
            for c in perfil["cnaes_desejados"]
        ]

        perfil_normalizado["municipio_alvo_ibge"] = (
            self.knn._codigo(
                perfil["municipio_alvo_ibge"], 7, "IBGE"
            )
        )

        # Classificador de conteúdo usa os pesos do perfil
        classificador = ClassificadorPorConteudo(*pesos)

        resultados_conteudo = classificador.recomendar(
            empresas_normalizadas,
            perfil_normalizado
        )

        possui_historico = bool(self.knn.historico)
        notas_knn = {}

        if possui_historico:
            resultados_knn = self.knn.recomendar(
                empresas_normalizadas,
                perfil_normalizado
            )

            for resultado in resultados_knn:
                notas_knn[resultado["cnpj"]] = resultado

        resultados_finais = []

        for resultado in resultados_conteudo:
            cnpj = resultado["cnpj"]
            nota_conteudo = resultado["pontuacao"]

            justificativas = [
                "Conteúdo: " + justificativa
                for justificativa in resultado["justificativas"]
            ]

            if possui_historico:
                if cnpj not in notas_knn:
                    raise ValueError(
                        f"KNN não retornou a empresa {cnpj}"
                    )

                nota_knn = notas_knn[cnpj]["pontuacao"]

                nota_final = (
                    self.peso_conteudo * nota_conteudo
                    + (1 - self.peso_conteudo) * nota_knn
                )

                justificativas.extend(
                    notas_knn[cnpj]["justificativas"]
                )

                justificativas.append(
                    f"Híbrido: {self.peso_conteudo:.0%} conteúdo "
                    f"+ {1 - self.peso_conteudo:.0%} KNN"
                )

            else:
                nota_knn = None
                nota_final = nota_conteudo

                justificativas.append(
                    "KNN não aplicado: histórico de "
                    "conversões indisponível"
                )

            resultados_finais.append({
                "cnpj": cnpj,
                "razao_social": resultado["razao_social"],
                "pontuacao": round(nota_final, 2),
                "justificativas": justificativas,
                "pontuacao_conteudo": nota_conteudo,
                "pontuacao_knn": nota_knn
            })

        resultados_finais.sort(
            key=lambda item: item["pontuacao"],
            reverse=True
        )

        return resultados_finais
