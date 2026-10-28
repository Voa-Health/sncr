"""Extração por blocos e compilação offline do Anexo I da Portaria 344."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

URL = (
    "https://anvisalegis.datalegis.net/action/ActionDatalegis.php?"
    "acao=abrirTextoAto&tipo=RDC&numeroAto=00001036&seqAto=000&valorAno=2026"
    "&orgao=RDC/DC/ANVISA/MS&codTipo=&desItem=&desItemFim=&cod_menu=1696"
    "&cod_modulo=134&pesquisa=true"
)
ATO = "RDC nº 1.036, de 09/07/2026"
BRUTO = Path("scripts/fontes/rdc1036.html")
METADADOS = Path("scripts/fontes/rdc1036.json")
DESTINO = Path("src/sncr/data/listas.json")
RELATORIO = Path("docs/extracao.md")
SIGLAS = (
    "A1",
    "A2",
    "A3",
    "B1",
    "B2",
    "C1",
    "C2",
    "C3",
    "C5",
    "D1",
    "D2",
    "E",
    "F1",
    "F2",
    "F3",
    "F4",
)
_ITEM = re.compile(r"^(\d+)\.\s*(.*)$")
_CABECALHO = re.compile(r"^LISTA\s*(?:-\s*([A-F]\d?)|(F[1-4])\s*-\s*(.+))$")


class Blocos(HTMLParser):
    """Reúna texto inline sem confundir quebras visuais com limites de parágrafo."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocos: list[str] = []
        self._partes: list[str] = []
        self._ignorar = 0

    def _fechar(self) -> None:
        texto = " ".join("".join(self._partes).split())
        if texto:
            self.blocos.append(texto)
        self._partes.clear()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Separe elementos de bloco e ignore conteúdo executável ou de estilo."""
        if tag in {"script", "style"}:
            self._ignorar += 1
        elif not self._ignorar and tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self._fechar()
        elif tag == "br" and not self._ignorar:
            self._partes.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """Finalize blocos preservando os elementos inline."""
        if tag in {"script", "style"}:
            self._ignorar = max(0, self._ignorar - 1)
        elif not self._ignorar and tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self._fechar()

    def handle_data(self, data: str) -> None:
        """Acumule texto legível do bloco."""
        if not self._ignorar:
            self._partes.append(data)

    def close(self) -> None:
        """Inclua o último bloco antes de encerrar a leitura."""
        super().close()
        self._fechar()


def blocos(conteudo: bytes) -> list[str]:
    """Decodifique a página oficial ISO-8859-1 em blocos de texto."""
    parser = Blocos()
    parser.feed(conteudo.decode("iso-8859-1"))
    parser.close()
    return parser.blocos


def atualizacao(textos: list[str]) -> int:
    """Extraia o número da atualização declarado no Anexo I."""
    for texto in textos:
        encontrado = re.search(r"ATUALIZAÇÃO\s+N[.º°]?\s*(\d+)", texto)
        if encontrado:
            return int(encontrado[1])
    raise ValueError("Número da atualização ausente na fonte.")


def json_bytes(dados: Any) -> bytes:
    """Serialize os artefatos com ordenação estável e quebra final."""
    return (json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def atualizar(root: Path) -> None:
    """Baixe e versione a página oficial com hash e data de obtenção."""
    with urllib.request.urlopen(URL, timeout=120) as resposta:
        bruto = resposta.read()
    numero = atualizacao(blocos(bruto))
    metadados = {
        "url": URL,
        "sha256": hashlib.sha256(bruto).hexdigest(),
        "atualizacao": numero,
        "ato": ATO,
        "data_obtencao": date.today().isoformat(),
    }
    (root / BRUTO).parent.mkdir(parents=True, exist_ok=True)
    (root / BRUTO).write_bytes(bruto)
    (root / METADADOS).write_bytes(json_bytes(metadados))


def _parentese_final(nome: str) -> tuple[str, list[str]]:
    """Extraia apenas um parêntese final balanceado precedido por espaço."""
    if not nome.endswith(")"):
        return nome, []
    nivel = 0
    for posicao in range(len(nome) - 1, -1, -1):
        if nome[posicao] == ")":
            nivel += 1
        elif nome[posicao] == "(":
            nivel -= 1
            if nivel == 0:
                if posicao > 0 and nome[posicao - 1].isspace():
                    return nome[:posicao].rstrip(" -"), [nome[posicao + 1 : -1]]
                break
    return nome, []


def substancia(texto: str) -> dict[str, Any]:
    """Separe nome, sinônimo parentético principal e alternativas explícitas."""
    partes = re.split(r"\s+ou\s+", texto, flags=re.IGNORECASE)
    nome, sinonimos = _parentese_final(partes[0])
    for alternativa in partes[1:]:
        designacoes = [parte.strip() for parte in alternativa.split(";")]
        ultima = designacoes[-1]
        if ultima.endswith(")") and ultima.count(")") > ultima.count("("):
            designacoes[-1] = ultima[:-1].rstrip()
        sinonimos.extend(parte for parte in designacoes if parte)
    return {"nome": nome, "sinonimos": list(dict.fromkeys(sinonimos))}


def extrair(conteudo: bytes) -> dict[str, Any]:
    """Compile listas, substâncias e adendos respeitando a ordem da norma."""
    catalogo: dict[str, Any] = {}
    atual: dict[str, Any] | None = None
    adendo = False
    pendente: list[str] = []
    numeros: list[int] = []
    titulo_f = ""

    def finalizar() -> None:
        if pendente and atual is not None:
            atual["substancias"].append(
                {
                    "numero": numeros[-1],
                    "original": " ".join(pendente),
                    **substancia(" ".join(pendente)),
                }
            )
            pendente.clear()

    def conferir() -> None:
        finalizar()
        if numeros and numeros[-1] != len(numeros):
            raise ValueError(f"Contagem divergente na lista {atual['sigla']}.")
        if atual is not None and not numeros:
            raise ValueError(f"Lista sem substâncias: {atual['sigla']}.")

    for texto in blocos(conteudo):
        cabecalho = _CABECALHO.fullmatch(texto)
        if cabecalho:
            conferir()
            sigla = cabecalho[1] or cabecalho[2]
            atual = None
            adendo = False
            numeros = []
            if sigla == "F":
                titulo_f = ""
            else:
                if sigla in catalogo:
                    raise ValueError(f"Lista repetida: {sigla}.")
                atual = {
                    "sigla": sigla,
                    "titulo": cabecalho[3] or "",
                    "descricao": titulo_f if sigla.startswith("F") else "",
                    "substancias": [],
                    "adendos": [],
                }
                catalogo[sigla] = atual
            continue
        if atual is None:
            if texto.startswith("LISTA DAS SUBSTÂNCIAS DE USO PROSCRITO"):
                titulo_f = texto
            continue
        if texto.startswith("PUB D.O.U."):
            conferir()
            atual = None
            break
        if texto == "ADENDO:":
            finalizar()
            adendo = True
            continue
        if re.match(r"^[b-d]\)\s+CLASSE", texto):
            finalizar()
            adendo = True
            atual["adendos"].append(texto)
            continue
        if adendo:
            if re.fullmatch(r"\d+\)\s*\(Excluído\)", texto, flags=re.IGNORECASE):
                continue
            if re.match(r"^\d+\)", texto):
                atual["adendos"].append(texto)
            elif atual["adendos"]:
                atual["adendos"][-1] += " " + texto
            else:
                raise ValueError(f"Adendo sem item na lista {atual['sigla']}.")
            continue
        item = _ITEM.fullmatch(texto)
        if item:
            finalizar()
            numeros.append(int(item[1]))
            if item[2]:
                pendente.append(item[2])
        elif numeros:
            pendente.append(texto)
        elif texto.startswith("(") and texto.endswith(")"):
            atual["descricao"] = texto[1:-1]
        elif not atual["titulo"]:
            atual["titulo"] = texto
    conferir()
    if tuple(catalogo) != SIGLAS:
        raise ValueError("Conjunto de listas diferente do Anexo I esperado.")
    return catalogo


def compilar(root: Path) -> bytes:
    """Verifique a integridade da fonte e gere JSON somente com dados locais."""
    bruto = (root / BRUTO).read_bytes()
    fonte = json.loads((root / METADADOS).read_text(encoding="utf-8"))
    if hashlib.sha256(bruto).hexdigest() != fonte["sha256"]:
        raise ValueError("SHA-256 da fonte divergente dos metadados.")
    if atualizacao(blocos(bruto)) != fonte["atualizacao"]:
        raise ValueError("Atualização divergente dos metadados.")
    return json_bytes({"fonte": fonte, "listas": extrair(bruto)})


def relatorio(dados: dict[str, Any]) -> bytes:
    """Liste contagens e todas as transformações de designações da fonte."""
    linhas = [
        "# Extração de designações",
        "",
        f"Atualização {dados['fonte']['atualizacao']} — {dados['fonte']['ato']}.",
        "",
        "## Contagem de substâncias",
        "",
        "| Lista | Itens |",
        "| --- | ---: |",
    ]
    linhas.extend(f"| {sigla} | {len(dados['listas'][sigla]['substancias'])} |" for sigla in SIGLAS)
    linhas.extend(
        [
            "",
            "## Nome principal e sinônimos",
            "",
            "Todas as aplicações de parêntese final, alternativa após ou ou separador ;.",
            "Alternativas preservam parênteses; só se remove um ) final excedente.",
            "A fonte repete o número 55 na lista F1; a numeração original foi preservada.",
            "As classes estruturais de F2 são pendências, não nomes para comparação exata.",
            "",
            "| Lista | Item | Original | Nome | Sinônimos |",
            "| --- | ---: | --- | --- | --- |",
        ]
    )
    for sigla in SIGLAS:
        for item in dados["listas"][sigla]["substancias"]:
            if not item["sinonimos"] and item["nome"] == item["original"]:
                continue
            campos = [
                sigla,
                str(item["numero"]),
                item["original"],
                item["nome"],
                " · ".join(item["sinonimos"]),
            ]
            linhas.append("| " + " | ".join(c.replace("|", r"\|") for c in campos) + " |")
    return ("\n".join(linhas) + "\n").encode()
