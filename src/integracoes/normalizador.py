
class Normalizador:
    """Normaliza os dados recebidos da BrasilAPI."""

    def normalizar_cnpj(self, dados: dict) -> dict:
        """Converte os dados para o formato do RadarLead."""

        if not isinstance(dados, dict):
            raise ValueError("Os dados devem ser um dicionario")

        obrigatorios = [
            "cnpj",
            "razao_social",
            "cnae_fiscal",
            "codigo_porte",
            "codigo_municipio_ibge"
        ]

        for campo in obrigatorios:
            valor = dados.get(campo)
            if valor is None or (
                isinstance(valor, str) and not valor.strip()
            ):
                raise ValueError(f"Campo obrigatorio ausente: {campo}")

        cnpj = str(dados["cnpj"]).strip()
        cnpj = cnpj.replace(".", "").replace("/", "").replace("-", "")

        if len(cnpj) != 14 or not cnpj.isdigit():
            raise ValueError("CNPJ deve conter 14 digitos")

        razao_social = dados["razao_social"]

        if not isinstance(razao_social, str):
            raise ValueError("Razao social deve ser um texto")

        razao_social = razao_social.strip()

        cnae = str(dados["cnae_fiscal"]).strip()

        if len(cnae) != 7 or not cnae.isdigit():
            raise ValueError("CNAE principal invalido")

        porte_original = dados["codigo_porte"]

        if isinstance(porte_original, bool):
            raise ValueError("Porte invalido")

        try:
            porte = int(porte_original)
        except (ValueError, TypeError, OverflowError) as erro:
            raise ValueError("Porte invalido") from erro

        if porte <= 0 or (
            isinstance(porte_original, float)
            and not porte_original.is_integer()
        ):
            raise ValueError("Porte invalido")

        municipio = str(dados["codigo_municipio_ibge"]).strip()

        if len(municipio) != 7 or not municipio.isdigit():
            raise ValueError("Codigo IBGE invalido")

        cep = dados.get("cep")

        if cep is not None:
            cep = str(cep).strip()
            if not cep:
                cep = None

        empresa = {
            "cnpj": cnpj,
            "razao_social": razao_social,
            "cnae_principal": cnae,
            "porte": porte,
            "municipio_ibge": municipio,
            "cnaes_secundarios": [],
            "cep": cep,
            "latitude": None,
            "longitude": None
        }

        return empresa
