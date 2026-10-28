"""Classificação exata por designações da norma, sujeita à revisão dos adendos."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from importlib.resources import files
from types import MappingProxyType

from sncr import tipos


@dataclass(frozen=True)
class Fonte:
    """Ato e número de atualização declarados na fonte versionada."""

    atualizacao: int
    ato: str


@dataclass(frozen=True)
class Substancia:
    """Designação principal e sinônimos, preservando o item original da norma."""

    numero: int
    original: str
    nome: str
    sinonimos: tuple[str, ...]


@dataclass(frozen=True)
class Lista:
    """Lista normativa com substâncias ordenadas e pendências para revisão humana."""

    sigla: str
    titulo: str
    descricao: str
    substancias: tuple[Substancia, ...]
    adendos: tuple[str, ...]


@dataclass(frozen=True)
class Classificacao:
    """Correspondência nominal, não uma autorização de prescrição ou dispensação."""

    consulta: str
    encontrada: bool
    listas: tuple[str, ...]
    receituarios: tuple[tipos.Tipo, ...]
    fonte: Fonte
    pendencias: tuple[str, ...]


def _normalizar(texto: str) -> str:
    decomposto = unicodedata.normalize("NFD", texto.casefold())
    sem_acentos = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return " ".join(sem_acentos.split())


def _carregar() -> tuple[Fonte, tuple[Lista, ...]]:
    dados = json.loads(files("sncr").joinpath("data/listas.json").read_text(encoding="utf-8"))
    fonte = Fonte(dados["fonte"]["atualizacao"], dados["fonte"]["ato"])
    catalogo = tuple(
        Lista(
            sigla=lista["sigla"],
            titulo=lista["titulo"],
            descricao=lista["descricao"],
            substancias=tuple(
                Substancia(
                    numero=item["numero"],
                    original=item["original"],
                    nome=item["nome"],
                    sinonimos=tuple(item["sinonimos"]),
                )
                for item in lista["substancias"]
            ),
            adendos=tuple(lista["adendos"]),
        )
        for lista in dados["listas"].values()
    )
    return fonte, catalogo


def _indexar(catalogo: tuple[Lista, ...]) -> dict[str, tuple[Lista, ...]]:
    indice: dict[str, list[Lista]] = {}
    for lista in catalogo:
        for item in lista.substancias:
            for nome in (item.nome, *item.sinonimos):
                chave = _normalizar(nome)
                if chave and lista not in indice.setdefault(chave, []):
                    indice[chave].append(lista)
    return {nome: tuple(listas) for nome, listas in indice.items()}


_FONTE, _LISTAS = _carregar()
_CATALOGO = MappingProxyType({lista.sigla: lista for lista in _LISTAS})
_INDICE = MappingProxyType(_indexar(_LISTAS))


def listas() -> tuple[Lista, ...]:
    """Retorne todas as listas na ordem da norma, sem permitir alterações."""
    return _LISTAS


def lista(sigla: str) -> Lista:
    """Obtenha uma lista por sigla; lance ValueError para sigla desconhecida."""
    try:
        return _CATALOGO[sigla.strip().upper()]
    except KeyError:
        raise ValueError(f"Sigla de lista desconhecida: {sigla!r}") from None


def classificar(substancia: str) -> Classificacao:
    """Compare nomes e sinônimos exatos; adendos exigem revisão humana."""
    encontradas = _INDICE.get(_normalizar(substancia), ())
    receituarios: list[tipos.Tipo] = []
    pendencias: list[str] = []
    for encontrada in encontradas:
        associados = tipos.para_lista(encontrada.sigla)
        for tipo in associados:
            if tipo not in receituarios:
                receituarios.append(tipo)
        pendencias.extend(encontrada.adendos)
        if not associados:
            pendencias.append(encontrada.descricao or encontrada.titulo)
    return Classificacao(
        consulta=substancia,
        encontrada=bool(encontradas),
        listas=tuple(item.sigla for item in encontradas),
        receituarios=tuple(receituarios),
        fonte=_FONTE,
        pendencias=tuple(pendencias),
    )
