"""Converte o ZIP oficial de CNAE-Subclasses 2.3 em JSON."""
import json
import re
import sys
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

with ZipFile(sys.argv[1]) as arquivo:
    nome, = [nome for nome in arquivo.namelist() if nome.endswith("Estrutura Detalhada.ods")]
    with ZipFile(BytesIO(arquivo.read(nome))) as planilha:
        estrutura = ElementTree.fromstring(planilha.read("content.xml"))

catalogo = {}
for linha in estrutura.iterfind(".//{*}table-row"):
    textos = ["".join(p.itertext()).strip() for celula in linha for p in celula.findall("{*}p")]
    if not textos or not re.fullmatch(r"[0-9]{4}-[0-9]/[0-9]{2}", textos[0]):
        continue
    codigo, *partes = textos
    descricao = " ".join(partes)
    codigo = re.sub(r"[-/]", "", codigo)
    if codigo in catalogo or not descricao:
        raise ValueError(f"Subclasse duplicada ou sem denominação: {codigo}")
    catalogo[codigo] = descricao

if len(catalogo) != 1332:
    raise ValueError(f"Esperadas 1332 subclasses da versão 2.3, obtidas {len(catalogo)}")

destino = Path(__file__).resolve().parents[1] / "src/data/cnaes.json"
dados = [{"codigo": codigo, "descricao": descricao} for codigo, descricao in sorted(catalogo.items())]
linhas = [json.dumps(item, ensure_ascii=False) for item in dados]
destino.write_text("[\n  " + ",\n  ".join(linhas) + "\n]\n", encoding="utf-8")
