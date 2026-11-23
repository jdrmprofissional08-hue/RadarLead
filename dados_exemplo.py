"""Empresas FICTÍCIAS para ver o sistema funcionando sem carga da Receita.

Todas são inventadas: os CNPJs têm dígitos verificadores propositalmente
inválidos (nunca coincidem com empresas reais) e os nomes não existem.
Servem apenas para o frontend receber leads durante o desenvolvimento.
"""

from src.dominio.empresa import Empresa

# (cnpj, razão social, cnae, porte, município IBGE, CEP, latitude, longitude, situação)
_EMPRESAS = [
    ("11111111000100", "Alfa Sistemas Demonstração Ltda", "6204000", 3, "5208707", "74000000", -16.6869, -49.2648, 2),
    ("22222222000100", "Beta Software Demonstração Ltda", "6204000", 1, "5208707", "74010000", -16.7100, -49.2400, 2),
    ("33333333000100", "Gama Tecnologia Demonstração S.A.", "6204000", 5, "5205109", "75700000", -18.1660, -47.9440, 2),
    ("44444444000100", "Delta Restaurante Demonstração Ltda", "5611201", 3, "5208707", "74020000", -16.6700, -49.2700, 2),
    ("55555555000100", "Épsilon Oficina Demonstração Ltda", "4520001", 1, "5205109", "75701000", -18.1500, -47.9300, 2),
    ("66666666000100", "Zeta Consultoria Demonstração Ltda", "6204000", 3, "5208707", "74030000", -16.6500, -49.2900, 8),
]

MUNICIPIOS = {"5208707": ("Goiânia", "GO"), "5205109": ("Catalão", "GO")}
CNAES = {
    "6204000": "Consultoria em tecnologia da informação",
    "5611201": "Restaurantes e similares",
    "4520001": "Manutenção e reparação mecânica de veículos",
}


def empresas_de_exemplo() -> list[Empresa]:
    return [
        Empresa(
            cnpj=cnpj, razao_social=razao, cnae_principal=cnae, porte=porte,
            municipio_ibge=ibge, cep=cep, latitude=lat, longitude=lon,
            situacao_cadastral=situacao,
        )
        for cnpj, razao, cnae, porte, ibge, cep, lat, lon, situacao in _EMPRESAS
    ]
