"""Gera o catálogo local a partir da edição do IBGE validada na UI-11E.2."""

import argparse
import hashlib
import json
import math
import re
import sqlite3
import struct
import tempfile
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ZIP_SHA256 = "1d96d5f0b379972a506d4b18c3696af974fbe59f8f6680557cb3a6dd38a0eb57"
GPKG_SHA256 = "d057a1638b16257f17338ea2b8a4fc1e0b4b4b93012c5a7fa294f44e401e2704"
GPKG = "BR_localidades_2022.gpkg"
FRONTEND = Path(__file__).resolve().parents[1]
CODIGO = re.compile(r"[0-9]{7}")


def sha256(dados):
    return hashlib.sha256(dados).hexdigest()


def ponto(geometria):
    if not isinstance(geometria, bytes) or len(geometria) < 8 or geometria[:3] != b"GP\x00":
        raise ValueError("Cabeçalho GeoPackage inválido")
    flags = geometria[3]
    envelopes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    envelope = (flags >> 1) & 7
    if flags & 0xf0 or envelope not in envelopes:
        raise ValueError("Geometria vazia ou não suportada")
    ordem = "<" if flags & 1 else ">"
    if struct.unpack_from(ordem + "i", geometria, 4)[0] != 4674:
        raise ValueError("A geometria deve usar EPSG:4674")
    wkb = geometria[8 + envelopes[envelope]:]
    if len(wkb) != 21 or wkb[0] not in (0, 1):
        raise ValueError("POINT 2D inválido")
    tipo, longitude, latitude = struct.unpack_from(("<" if wkb[0] else ">") + "Idd", wkb, 1)
    if (tipo != 1 or not all(map(math.isfinite, (latitude, longitude)))
            or not (-90 <= latitude <= 90 and -180 <= longitude <= 180)):
        raise ValueError("POINT ou coordenadas inválidos")
    return latitude, longitude


def consolidar(registros):
    pontos = {}
    duplicados = set()
    total = 0
    for codigo, geometria in registros:
        total += 1
        if not isinstance(codigo, str) or not CODIGO.fullmatch(codigo):
            raise ValueError(f"Código municipal inválido: {codigo!r}")
        par = ponto(geometria)
        if codigo in pontos:
            if pontos[codigo] != par:
                raise ValueError(f"Coordenadas conflitantes para {codigo}")
            duplicados.add(codigo)
        pontos[codigo] = par
    return pontos, duplicados, total


def extrair(arquivo):
    if sha256(arquivo.read_bytes()) != ZIP_SHA256:
        raise ValueError("SHA-256 do ZIP diverge da versão oficial esperada")
    with ZipFile(arquivo) as zip_oficial:
        if zip_oficial.namelist() != [GPKG]:
            raise ValueError("O ZIP deve conter somente o GeoPackage esperado")
        dados = zip_oficial.read(GPKG)
    if sha256(dados) != GPKG_SHA256:
        raise ValueError("SHA-256 do GeoPackage diverge da versão oficial esperada")
    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / GPKG
        caminho.write_bytes(dados)
        conexao = sqlite3.connect(caminho.as_uri() + "?mode=ro", uri=True)
        try:
            camada = conexao.execute("""
                SELECT tabela.srs_id, geometria.srs_id, geometria.geometry_type_name,
                       geometria.z, geometria.m, ref.organization, ref.organization_coordsys_id
                FROM gpkg_contents AS tabela
                JOIN gpkg_geometry_columns AS geometria ON tabela.table_name = geometria.table_name
                JOIN gpkg_spatial_ref_sys AS ref ON geometria.srs_id = ref.srs_id
                WHERE tabela.table_name = 'BR_localidades_2022' AND geometria.column_name = 'geom'
            """).fetchone()
            if camada != (4674, 4674, "POINT", 0, 0, "EPSG", 4674):
                raise ValueError(f"Metadados de camada inesperados: {camada}")
            registros = conexao.execute("""
                SELECT CD_MUN, geom FROM BR_localidades_2022
                WHERE (CT_LOCALIDADE = 'Cidade' AND SCT_LOCALIDADE IN
                       ('Sede Municipal', 'Capital Estadual', 'Capital Federal'))
                   OR (CT_LOCALIDADE = 'Distrito Estadual de Fernando de Noronha' AND CD_MUN = '2605459')
            """)
            return consolidar(registros)
        finally:
            conexao.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="ZIP oficial já baixado, fora do repositório")
    args = parser.parse_args()
    try:
        pontos, duplicados, total = extrair(args.zip)
        municipios = json.loads((FRONTEND / "src/data/municipios.json").read_text(encoding="utf-8"))
        codigos = {m["codigo"] for m in municipios}
        ausentes = sorted(codigos - pontos.keys())
        adicionais = sorted(pontos.keys() - codigos)
        cobertura = len(codigos & pontos.keys()) / len(codigos)
        print(f"Candidatos: {total}. Códigos duplicados equivalentes: {len(duplicados)}.")
        print(f"Códigos finais: {len(pontos)}. Cobertura: {cobertura:.2%}.")
        print(f"Ausentes: {ausentes}. Adicionais: {adicionais}.")
        if ausentes or adicionais or len(municipios) != 5571 or (total, len(duplicados), len(pontos)) != (5597, 26, 5571):
            raise ValueError("Cobertura ou contagens divergentes. O catálogo não foi atualizado")
        arredondados = {codigo: [round(valor, 6) for valor in par] for codigo, par in pontos.items()}
        saida = (json.dumps(arredondados, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        destino = FRONTEND / ".dados-locais/coordenadas-municipios.json"
        destino.parent.mkdir(exist_ok=True)
        # A troca no mesmo diretório evita servir conteúdo parcialmente gravado pelo Vite.
        with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as temporario:
            temporario.write(saida)
        Path(temporario.name).replace(destino)
        print(f"SHA-256 da saída: {sha256(saida)}. Arquivo local: {destino}")
    except (ValueError, OSError, BadZipFile, sqlite3.Error) as erro:
        parser.exit(1, f"Erro: {erro}\n")


if __name__ == "__main__":
    main()
