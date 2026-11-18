
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class ClienteBrasilAPI:
    """Cliente responsável por consultar dados na BrasilAPI."""

    BASE_URL = "https://brasilapi.com.br/api"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def consultar_cnpj(self, cnpj: str) -> dict:
        """Consulta um CNPJ e retorna os dados recebidos."""

        if not isinstance(cnpj, str):
            raise ValueError("CNPJ deve ser um texto")

        cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")
        cnpj = cnpj.strip()

        if len(cnpj) != 14 or not cnpj.isdigit():
            raise ValueError("CNPJ invalido")

        url = f"{self.BASE_URL}/cnpj/v1/{cnpj}"
        requisicao = Request(
            url,
            headers={"Accept": "application/json"}
        )

        try:
            with urlopen(requisicao, timeout=self.timeout) as resposta:
                dados = json.load(resposta)

        except HTTPError as erro:
            if erro.code == 404:
                raise ValueError("CNPJ nao encontrado") from erro

            raise ConnectionError(
                f"Erro HTTP na BrasilAPI: {erro.code}"
            ) from erro

        except (URLError, TimeoutError, OSError) as erro:
            raise ConnectionError(
                "Nao foi possivel conectar a BrasilAPI"
            ) from erro

        except (json.JSONDecodeError, UnicodeDecodeError) as erro:
            raise ValueError(
                "A BrasilAPI retornou um JSON invalido"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError("Resposta da BrasilAPI invalida")

        return dados

    def consultar_cep(self, cep: str) -> dict:
        """Consulta um CEP na BrasilAPI e retorna os dados."""

        if not isinstance(cep, str):
            raise ValueError("CEP deve ser um texto")

        cep = cep.strip().replace("-", "")

        if len(cep) != 8 or not cep.isdigit():
            raise ValueError("CEP deve conter 8 digitos")

        url = f"{self.BASE_URL}/cep/v2/{cep}"
        requisicao = Request(
            url,
            headers={"Accept": "application/json"}
        )

        try:
            with urlopen(requisicao, timeout=self.timeout) as resposta:
                dados = json.load(resposta)

        except HTTPError as erro:
            if erro.code == 404:
                raise ValueError("CEP nao encontrado") from erro

            raise ConnectionError(
                f"Erro HTTP na BrasilAPI: {erro.code}"
            ) from erro

        except (URLError, TimeoutError, OSError) as erro:
            raise ConnectionError(
                "Nao foi possivel conectar a BrasilAPI"
            ) from erro

        except (json.JSONDecodeError, UnicodeDecodeError) as erro:
            raise ValueError(
                "A BrasilAPI retornou um JSON invalido"
            ) from erro

        if not isinstance(dados, dict):
            raise ValueError("Resposta da BrasilAPI invalida")

        return dados
