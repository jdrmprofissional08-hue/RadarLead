
import math


class FiltroElegibilidade:
    def __init__(self, cnaes_diretos, cnaes_relacionados,
                 raio_max_km=350):

        self.cnaes_diretos = {
            str(cnae).zfill(7) for cnae in cnaes_diretos
        }

        self.cnaes_relacionados = {
            str(cnae).zfill(7) for cnae in cnaes_relacionados
        }

        self.raio_max_km = raio_max_km

    def eliminar(self, cnpj, motivo):
        return {
            "cnpj": cnpj,
            "aprovada": False,
            "motivo": motivo,
            "compatibilidade": None,
            "fator_atividade": 0,
            "distancia_km": None
        }

    @staticmethod
    def validar_coordenadas(latitude, longitude):
        try:
            if latitude is None or longitude is None:
                return None

            lat = float(latitude)
            lon = float(longitude)

            if not math.isfinite(lat) or not math.isfinite(lon):
                return None

            if not (-90 <= lat <= 90):
                return None

            if not (-180 <= lon <= 180):
                return None

            return lat, lon

        except (ValueError, TypeError, OverflowError):
            return None

    @staticmethod
    def calcular_distancia(lat1, lon1, lat2, lon2):
        raio_terra = 6371.0

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1)
            * math.cos(lat2)
            * math.sin(delta_lon / 2) ** 2
        )

        a = min(1.0, max(0.0, a))

        return 2 * raio_terra * math.asin(math.sqrt(a))

    def verificar_atividade(self, dados_cnpj):
        principal = str(dados_cnpj.get("cnae_fiscal", ""))

        secundarios = dados_cnpj.get("cnaes_secundarios") or []

        cnaes = {principal.zfill(7)}

        if isinstance(secundarios, list):
            for item in secundarios:
                if isinstance(item, dict):
                    codigo = item.get("codigo")
                    if codigo is not None:
                        cnaes.add(str(codigo).zfill(7))

        if cnaes.intersection(self.cnaes_diretos):
            return "direta", 1.0

        if cnaes.intersection(self.cnaes_relacionados):
            return "relacionada", 0.6

        return None, 0

    def avaliar(self, dados_cnpj, dados_cep, fornecedor):
        cnpj = None

        if not isinstance(dados_cnpj, dict):
            return self.eliminar(
                cnpj, "Dados de CNPJ indisponíveis"
            )

        cnpj = dados_cnpj.get("cnpj")

        if not isinstance(cnpj, str):
            return self.eliminar(cnpj, "CNPJ inválido")

        if len(cnpj) != 14 or not cnpj.isdigit():
            return self.eliminar(cnpj, "CNPJ inválido")

        situacao = dados_cnpj.get("situacao_cadastral")

        if str(situacao).strip() != "2":
            return self.eliminar(
                cnpj, "Empresa não está ativa"
            )

        cnae_principal = dados_cnpj.get("cnae_fiscal")

        if cnae_principal is None:
            return self.eliminar(
                cnpj, "CNAE principal ausente"
            )

        codigo_principal = str(cnae_principal)

        if not codigo_principal.isdigit() or len(codigo_principal) > 7:
            return self.eliminar(
                cnpj, "CNAE principal inválido"
            )

        compatibilidade, fator = self.verificar_atividade(
            dados_cnpj
        )

        if compatibilidade is None:
            return self.eliminar(
                cnpj, "Atividade econômica incompatível"
            )

        cep_cnpj = dados_cnpj.get("cep")

        if not isinstance(cep_cnpj, str):
            return self.eliminar(cnpj, "CEP ausente ou inválido")

        cep_cnpj = cep_cnpj.replace("-", "").strip()

        if len(cep_cnpj) != 8 or not cep_cnpj.isdigit():
            return self.eliminar(cnpj, "CEP ausente ou inválido")

        if not isinstance(dados_cep, dict):
            return self.eliminar(
                cnpj, "Consulta de CEP indisponível"
            )

        cep_consultado = dados_cep.get("cep")

        if not isinstance(cep_consultado, str):
            return self.eliminar(
                cnpj, "CEP consultado inválido"
            )

        cep_consultado = cep_consultado.replace("-", "").strip()

        if cep_cnpj != cep_consultado:
            return self.eliminar(
                cnpj, "CEP consultado não corresponde ao CNPJ"
            )

        location = dados_cep.get("location")

        if not isinstance(location, dict):
            return self.eliminar(
                cnpj, "Geolocalização indisponível"
            )

        coordenadas = location.get("coordinates")

        if not isinstance(coordenadas, dict):
            return self.eliminar(
                cnpj, "Geolocalização indisponível"
            )

        destino = self.validar_coordenadas(
            coordenadas.get("latitude"),
            coordenadas.get("longitude")
        )

        if destino is None:
            return self.eliminar(
                cnpj, "Coordenadas da empresa inválidas"
            )

        if not isinstance(fornecedor, dict):
            return self.eliminar(
                cnpj, "Localização do fornecedor indisponível"
            )

        origem = self.validar_coordenadas(
            fornecedor.get("latitude"),
            fornecedor.get("longitude")
        )

        if origem is None:
            return self.eliminar(
                cnpj, "Coordenadas do fornecedor inválidas"
            )

        distancia = self.calcular_distancia(
            origem[0], origem[1],
            destino[0], destino[1]
        )

        if not isinstance(self.raio_max_km, (int, float)):
            return self.eliminar(
                cnpj, "Limite de distância inválido"
            )

        if not math.isfinite(self.raio_max_km) or self.raio_max_km < 0:
            return self.eliminar(
                cnpj, "Limite de distância inválido"
            )

        if distancia > self.raio_max_km:
            return self.eliminar(
                cnpj, "Distância acima do limite permitido"
            )

        return {
            "cnpj": cnpj,
            "aprovada": True,
            "motivo": "Empresa elegível para classificação",
            "compatibilidade": compatibilidade,
            "fator_atividade": fator,
            "distancia_km": round(distancia, 2)
        }
