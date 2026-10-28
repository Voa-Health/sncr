"""Medição offline de correspondência nominal sobre apresentações da CMED."""

from __future__ import annotations

import csv
import hashlib
import io
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from zipfile import ZipFile

from sncr import listas

URL = (
    "https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/precos/arquivos/"
    "lista_pmc__20261009_115232672.xlsx/@@download/file"
)
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _xlsx(conteudo: bytes) -> Iterator[dict[str, str]]:
    with ZipFile(io.BytesIO(conteudo)) as arquivo:
        strings = []
        if "xl/sharedStrings.xml" in arquivo.namelist():
            strings = [
                "".join(no.itertext()) for no in ET.fromstring(arquivo.read("xl/sharedStrings.xml"))
            ]
        for folha in sorted(arquivo.namelist()):
            if not folha.startswith("xl/worksheets/sheet") or not folha.endswith(".xml"):
                continue
            cabecalho: dict[str, str] = {}
            with arquivo.open(folha) as entrada:
                for _, no in ET.iterparse(entrada, events=("end",)):
                    if no.tag != _NS + "row":
                        continue
                    celulas = {}
                    for celula in no:
                        coluna = "".join(c for c in celula.attrib["r"] if c.isalpha())
                        valor = celula.findtext(_NS + "v", "")
                        if celula.get("t") == "s":
                            valor = strings[int(valor)]
                        elif celula.get("t") == "inlineStr":
                            valor = "".join(t.text or "" for t in celula.iter(_NS + "t"))
                        celulas[coluna] = valor.strip()
                    if {"SUBSTÂNCIA", "TARJA", "APRESENTAÇÃO"} <= set(celulas.values()):
                        cabecalho = celulas
                    elif cabecalho:
                        linha = {
                            nome: celulas.get(coluna, "") for coluna, nome in cabecalho.items()
                        }
                        if linha.get("SUBSTÂNCIA"):
                            yield linha
                    no.clear()


def ler(conteudo: bytes) -> list[dict[str, str]]:
    """Leia XLSX ou CSV com cabeçalho CMED, rejeitando fontes sem tarja."""
    if conteudo.startswith(b"PK"):
        linhas = list(_xlsx(conteudo))
    else:
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = conteudo.decode("cp1252")
        linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
    if not linhas or not {"SUBSTÂNCIA", "TARJA", "APRESENTAÇÃO"} <= linhas[0].keys():
        raise ValueError("Fonte sem apresentações ou colunas SUBSTÂNCIA, TARJA e APRESENTAÇÃO.")
    return linhas


def principios(substancia: str) -> tuple[str, ...]:
    """Separe compostos pelo ponto e vírgula usado pela planilha oficial."""
    return tuple(parte.strip() for parte in substancia.split(";") if parte.strip())


@cache
def correspondencias(substancia: str) -> tuple[bool, bool]:
    """Conte apresentação como correspondente quando algum princípio casar."""
    resultados = [listas.classificar(principio) for principio in principios(substancia)]
    return (
        any(r.encontrada and not r.por_derivado for r in resultados),
        any(r.encontrada for r in resultados),
    )


def relatorio(conteudo: bytes, url: str = URL) -> str:
    """Produza tabela estável por tarja com proveniência e definição da contagem."""
    contagens: dict[str, list[int]] = {}
    for linha in ler(conteudo):
        tarja = linha["TARJA"].strip() or "(vazia)"
        valores = contagens.setdefault(tarja, [0, 0, 0])
        exato, incluido = correspondencias(linha["SUBSTÂNCIA"])
        valores[0] += 1
        valores[1] += exato
        valores[2] += incluido
    saida = [
        f"URL: {url}",
        f"SHA256: {hashlib.sha256(conteudo).hexdigest()}",
        "Unidade: linha de apresentação; casa se algum princípio casar; compostos separados por ;.",
        "TARJA\tTOTAL\tEXATO\tCOM DERIVADO\tCOBERTURA (%)",
    ]
    for tarja, (total, exatos, incluidos) in sorted(contagens.items()):
        saida.append(f"{tarja}\t{total}\t{exatos}\t{incluidos}\t{100 * incluidos / total:.2f}")
    return "\n".join(saida) + "\n"


def cobertura(arquivo: Path | None, url: str = URL) -> str:
    """Leia arquivo local ou baixe a fonte oficial sem persistir o conteúdo."""
    if arquivo is not None:
        conteudo = arquivo.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=120) as resposta:
            conteudo = resposta.read()
    return relatorio(conteudo, url)
