

import math

import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import OrdinalEncoder

from src.Recomendadores.base import Recomendador


class RecomendadorKNN(Recomendador):
    """KNN supervisionado: aprende com histórico de conversões."""

    def __init__(self, historico=None, k=3):
        if type(k) is not int or k < 1:
            raise ValueError("k deve ser um inteiro positivo")

        self.k = k
        self.historico = []

        if historico is not None:
            self.treinar(historico)

    @staticmethod
    def _codigo(valor, tamanho, nome):
        if isinstance(valor, bool) or not isinstance(valor, (int, str)):
            raise ValueError(f"{nome} inválido")

        texto = str(valor)

        if not texto.isdigit() or len(texto) > tamanho or not texto:
            raise ValueError(f"{nome} inválido")

        return texto.zfill(tamanho)

    @classmethod
    def _preparar_empresa(cls, empresa):
        if not isinstance(empresa, dict):
            raise ValueError("Empresa deve ser um dicionário")

        porte = empresa.get("porte")

        if type(porte) is not int or porte not in (0, 1, 3, 5):
            raise ValueError("Porte empresarial inválido")

        return {
            "cnpj": cls._codigo(empresa.get("cnpj"), 14, "CNPJ"),
            "razao_social": empresa.get("razao_social") or "",
            "cnae_principal": cls._codigo(
                empresa.get("cnae_principal"), 7, "CNAE"
            ),
            "porte": str(porte),
            "municipio_ibge": cls._codigo(
                empresa.get("municipio_ibge"), 7, "IBGE"
            ),
        }

    @staticmethod
    def _pesos(perfil):
        if not isinstance(perfil, dict):
            raise ValueError("Perfil deve ser um dicionário")

        nomes = (
            "peso_cnae",
            "peso_porte",
            "peso_localizacao"
        )

        padrao = (50, 25, 25)

        valores = [
            perfil.get(nome, default)
            for nome, default in zip(nomes, padrao)
        ]

        # Aceita pesos decimais e mantém a mesma
        # validação utilizada no domínio Perfil.
        for valor in valores:
            if (
                isinstance(valor, bool)
                or not isinstance(valor, (int, float))
                or not math.isfinite(valor)
                or not 0 <= valor <= 100
                or round(valor, 2) != valor
            ):
                raise ValueError(
                    "Pesos devem ser números entre 0 e 100 "
                    "com até duas casas decimais"
                )

        if not math.isclose(
            sum(valores),
            100,
            rel_tol=0,
            abs_tol=1e-9
        ):
            raise ValueError(
                "A soma dos pesos deve ser 100"
            )

        return np.asarray(valores, dtype=float) / 100.0

    @staticmethod
    def _atributos(empresa):
        return [
            empresa["cnae_principal"],
            empresa["porte"],
            empresa["municipio_ibge"]
        ]

    def treinar(self, historico):
        if not isinstance(historico, list):
            raise ValueError("Histórico deve ser uma lista")

        novos = []
        vistos = set()

        for item in historico:
            empresa = self._preparar_empresa(item)

            if type(item.get("converteu")) is not bool:
                raise ValueError(
                    "Histórico exige 'converteu' booleano"
                )

            if empresa["cnpj"] in vistos:
                raise ValueError("CNPJ repetido no histórico")

            vistos.add(empresa["cnpj"])

            empresa["converteu"] = item["converteu"]
            novos.append(empresa)

        self.historico = novos

    def recomendar(self, empresas: list, perfil: dict) -> list:
        if not isinstance(empresas, list):
            raise ValueError("Empresas deve ser uma lista")

        pesos = self._pesos(perfil)

        if not empresas:
            return []

        if not self.historico:
            raise ValueError(
                "KNN exige histórico rotulado de conversões"
            )

        def distancia(a, b):
            return float(np.dot(pesos, a != b))

        resultados = []

        for item in empresas:
            candidata = self._preparar_empresa(item)

            # Exclui a própria empresa do histórico.
            treino = [
                h for h in self.historico
                if h["cnpj"] != candidata["cnpj"]
            ]

            if not treino:
                raise ValueError(
                    "Sem vizinhos históricos independentes "
                    "para esta empresa"
                )

            encoder = OrdinalEncoder(
                handle_unknown="use_encoded_value",
                unknown_value=-1
            )

            X_treino = encoder.fit_transform([
                self._atributos(h) for h in treino
            ])

            X_candidata = encoder.transform([
                self._atributos(candidata)
            ])

            quantidade = min(self.k, len(treino))

            modelo = NearestNeighbors(
                n_neighbors=quantidade,
                algorithm="brute",
                metric=distancia
            )

            modelo.fit(X_treino)

            distancias, indices = modelo.kneighbors(X_candidata)

            positivos = sum(
                treino[int(i)]["converteu"]
                for i in indices[0]
            )

            resultados.append({
                "cnpj": candidata["cnpj"],
                "razao_social": candidata["razao_social"],
                "pontuacao": round(
                    100 * positivos / quantidade, 2
                ),
                "justificativas": [
                    (
                        f"KNN: {positivos} de "
                        f"{quantidade} vizinhos converteram"
                    ),
                    (
                        "Distância categórica mínima: "
                        f"{float(distancias[0][0]):.2f}"
                    )
                ],
            })

        return sorted(
            resultados,
            key=lambda r: r["pontuacao"],
            reverse=True
        )
