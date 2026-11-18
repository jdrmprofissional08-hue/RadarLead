
from src.Recomendadores.base import Recomendador
from src.Recomendadores.filtro_elegibilidade import FiltroElegibilidade


class RecomendadorComFiltro(Recomendador):
    """
    Aplica a elegibilidade antes de chamar outro recomendador.

    Recebe empresas já normalizadas.
    O retorno de recomendar() segue o contrato do backend:
    list[dict].
    """

    def __init__(self, recomendador, filtro, fornecedor):
        if not isinstance(recomendador, Recomendador):
            raise TypeError(
                "O recomendador deve implementar Recomendador"
            )

        if not isinstance(filtro, FiltroElegibilidade):
            raise TypeError(
                "O filtro deve ser um FiltroElegibilidade"
            )

        self.recomendador = recomendador
        self.filtro = filtro
        self.fornecedor = fornecedor
        self.eliminadas = []
        self.aprovadas = []
        self.total_avaliadas = 0

    @staticmethod
    def _codigo(valor, tamanho):
        if isinstance(valor, bool):
            return None

        if not isinstance(valor, (str, int)):
            return None

        texto = str(valor)

        if not texto.isdigit() or not 1 <= len(texto) <= tamanho:
            return None

        return texto.zfill(tamanho)

    @staticmethod
    def _cep(valor):
        if not isinstance(valor, str):
            return None

        texto = valor.replace("-", "").strip()

        if len(texto) != 8 or not texto.isdigit():
            return None

        return texto

    def _eliminar(self, cnpj, motivo):
        self.eliminadas.append({
            "cnpj": cnpj,
            "aprovada": False,
            "pontuacao": 0,
            "motivo": motivo
        })

    def _avaliar_empresa(self, dados):
        if not isinstance(dados, dict):
            return None, "Dados da empresa inválidos"

        cnpj = self._codigo(dados.get("cnpj"), 14)

        if cnpj is None:
            return None, "CNPJ inválido"

        situacao = dados.get("situacao_cadastral")

        if str(situacao).strip() != "2":
            return None, "Empresa inativa ou situação desconhecida"

        cnae = self._codigo(
            dados.get("cnae_principal"), 7
        )

        if cnae is None:
            return None, "CNAE principal inválido"

        secundarios = dados.get("cnaes_secundarios", [])

        if not isinstance(secundarios, list):
            return None, "CNAEs secundários inválidos"

        secundarios_normalizados = []

        for codigo in secundarios:
            normalizado = self._codigo(codigo, 7)

            if normalizado is None:
                return None, "CNAE secundário inválido"

            secundarios_normalizados.append(normalizado)

        atividade = {
            "cnae_fiscal": cnae,
            "cnaes_secundarios": [
                {"codigo": codigo}
                for codigo in secundarios_normalizados
            ]
        }

        compatibilidade, fator = (
            self.filtro.verificar_atividade(atividade)
        )

        if compatibilidade is None:
            return None, "Atividade econômica incompatível"

        porte = dados.get("porte")

        if type(porte) is not int or porte not in (0, 1, 3, 5):
            return None, "Porte empresarial inválido"

        municipio = self._codigo(
            dados.get("municipio_ibge"), 7
        )

        if municipio is None:
            return None, "Município IBGE inválido"

        cep = self._cep(dados.get("cep"))

        if cep is None:
            return None, "CEP ausente ou inválido"

        nome = dados.get("razao_social")

        if not isinstance(nome, str) or not nome.strip():
            return None, "Razão social inválida"

        destino = self.filtro.validar_coordenadas(
            dados.get("latitude"),
            dados.get("longitude")
        )

        if destino is None:
            return None, "Geolocalização indisponível ou inválida"

        distancia = self.filtro.calcular_distancia(
            self.origem[0],
            self.origem[1],
            destino[0],
            destino[1]
        )

        if distancia > self.filtro.raio_max_km:
            return None, "Distância acima do limite permitido"

        empresa = {
            "cnpj": cnpj,
            "razao_social": nome.strip(),
            "situacao_cadastral": 2,
            "cnae_principal": cnae,
            "cnaes_secundarios": secundarios_normalizados,
            "porte": porte,
            "municipio_ibge": municipio,
            "cep": cep,
            "latitude": destino[0],
            "longitude": destino[1]
        }

        return empresa, {
            "compatibilidade": compatibilidade,
            "fator_atividade": fator,
            "distancia_km": round(distancia, 2)
        }

    def recomendar(self, empresas: list, perfil: dict) -> list:
        if not isinstance(empresas, list):
            raise ValueError("Empresas deve ser uma lista")

        if not isinstance(perfil, dict):
            raise ValueError("Perfil deve ser um dicionário")

        self.eliminadas = []
        self.aprovadas = []
        self.total_avaliadas = len(empresas)

        self.origem = self.filtro.validar_coordenadas(
            self.fornecedor.get("latitude")
            if isinstance(self.fornecedor, dict) else None,
            self.fornecedor.get("longitude")
            if isinstance(self.fornecedor, dict) else None
        )

        if self.origem is None:
            raise ValueError(
                "Coordenadas do fornecedor indisponíveis"
            )

        if (
            isinstance(self.filtro.raio_max_km, bool)
            or not isinstance(
                self.filtro.raio_max_km, (int, float)
            )
            or not 0 <= self.filtro.raio_max_km <= 350
        ):
            raise ValueError("Raio de busca inválido")

        aptas = []
        metadados = {}
        cnpjs_vistos = set()

        for dados in empresas:
            cnpj_original = (
                dados.get("cnpj")
                if isinstance(dados, dict)
                else None
            )

            empresa, resultado = self._avaliar_empresa(dados)

            if empresa is None:
                self._eliminar(cnpj_original, resultado)
                continue

            cnpj = empresa["cnpj"]

            if cnpj in cnpjs_vistos:
                self._eliminar(cnpj, "CNPJ duplicado")
                continue

            cnpjs_vistos.add(cnpj)
            aptas.append(empresa)
            metadados[cnpj] = resultado

            self.aprovadas.append({
                "cnpj": cnpj,
                "aprovada": True,
                **resultado
            })

        if not aptas:
            return []

        # O recomendador pode ser de conteúdo, KNN ou híbrido.
        recomendacoes = self.recomendador.recomendar(
            aptas, perfil
        )

        if not isinstance(recomendacoes, list):
            raise ValueError(
                "O recomendador deve retornar uma lista"
            )

        resultados = []
        retornados = set()

        for item in recomendacoes:
            if not isinstance(item, dict):
                raise ValueError("Recomendação inválida")

            cnpj = item.get("cnpj")

            if cnpj not in metadados or cnpj in retornados:
                raise ValueError(
                    "Recomendador retornou CNPJ inválido ou duplicado"
                )

            nota = item.get("pontuacao")

            if (
                isinstance(nota, bool)
                or not isinstance(nota, (int, float))
                or not 0 <= nota <= 100
            ):
                raise ValueError("Pontuação inválida")

            justificativas = item.get("justificativas")

            if not isinstance(justificativas, list):
                raise ValueError("Justificativas inválidas")

            resultado = dict(item)
            resultado["distancia_km"] = metadados[cnpj][
                "distancia_km"
            ]
            resultado["compatibilidade"] = metadados[cnpj][
                "compatibilidade"
            ]

            resultados.append(resultado)
            retornados.add(cnpj)

        if len(retornados) != len(aptas):
            raise ValueError(
                "Recomendador não retornou todas as empresas aptas"
            )

        resultados.sort(
            key=lambda item: item["pontuacao"],
            reverse=True
        )

        return resultados
