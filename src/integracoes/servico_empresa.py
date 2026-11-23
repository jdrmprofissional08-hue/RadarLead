
from src.integracoes.brasilapi import ClienteBrasilAPI
from src.integracoes.normalizador import Normalizador


class ServicoConsultaEmpresa:
    """Consulta CNPJ e CEP e prepara os dados da empresa."""

    def __init__(self, cliente=None, normalizador=None):
        self.cliente = (
            cliente if cliente is not None else ClienteBrasilAPI()
        )
        self.normalizador = (
            normalizador if normalizador is not None else Normalizador()
        )

    def consultar_dados(self, cnpj: str) -> dict:
        """Devolve os dados normalizados para o RadarLead."""

        # 1. Consulta e normaliza o CNPJ.
        dados_cnpj = self.cliente.consultar_cnpj(cnpj)
        empresa = self.normalizador.normalizar_cnpj(dados_cnpj)

        # 2. Verifica se existe um CEP para consultar.
        cep = empresa.get("cep")

        if not cep:
            raise ValueError(
                "A empresa nao possui CEP para completar o cadastro"
            )

        # 3. Consulta e normaliza o endereco.
        dados_cep = self.cliente.consultar_cep(cep)
        endereco = self.normalizador.normalizar_cep(dados_cep)

        # 4. Confere se o CEP retornado corresponde ao solicitado.
        cep_limpo = str(cep).replace("-", "").replace(".", "")

        if cep_limpo != endereco["cep"]:
            raise ValueError(
                "O CEP retornado nao corresponde ao CEP da empresa"
            )

        # 5. Confere divergencias entre os codigos IBGE.
        ibge_cep = endereco.get("municipio_ibge")
        ibge_empresa = empresa["municipio_ibge"]

        if ibge_cep is not None and ibge_cep != ibge_empresa:
            raise ValueError(
                "Municipio do CEP diverge do municipio do CNPJ"
            )

        # 6. Reune as informacoes.
        empresa["cep"] = endereco["cep"]
        empresa["latitude"] = endereco["latitude"]
        empresa["longitude"] = endereco["longitude"]

        return empresa
