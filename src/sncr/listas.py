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
    derivados: Derivados


@dataclass(frozen=True)
class Derivados:
    """Extensões gerais de controle declaradas pelos adendos da lista."""

    sais: bool
    eteres: bool
    esteres: bool
    isomeros: bool
    excecoes: tuple[str, ...]


@dataclass(frozen=True)
class Classificacao:
    """Correspondência nominal, não uma autorização de prescrição ou dispensação."""

    consulta: str
    encontrada: bool
    listas: tuple[str, ...]
    receituarios: tuple[tipos.Tipo, ...]
    fonte: Fonte
    pendencias: tuple[str, ...]
    forma_base: str | None = None
    por_derivado: bool = False


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
            derivados=Derivados(
                **{
                    chave: lista["derivados"][chave]
                    for chave in ("sais", "eteres", "esteres", "isomeros")
                },
                excecoes=tuple(lista["derivados"]["excecoes"]),
            ),
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
_FORMAS = tuple(
    (_normalizar(forma["texto"]), forma["posicao"], forma["tipo"])
    for forma in json.loads(files("sncr").joinpath("data/derivados.json").read_text("utf-8"))
)


def _por_derivado(consulta: str) -> tuple[tuple[Lista, ...], str | None]:
    """Procure bases removendo apenas formas versionadas permitidas pela lista."""
    pendentes = [(consulta, frozenset[str]())]
    visitadas: set[tuple[str, frozenset[str]]] = set()
    campos = {"sal": "sais", "ester": "esteres", "eter": "eteres"}
    while pendentes:
        nome, tipos_removidos = pendentes.pop(0)
        if (nome, tipos_removidos) in visitadas:
            continue
        visitadas.add((nome, tipos_removidos))
        if nome != consulta:
            candidatas = tuple(
                lista
                for lista in _INDICE.get(nome, ())
                if all(getattr(lista.derivados, campos[tipo]) for tipo in tipos_removidos)
                and nome not in {_normalizar(e) for e in lista.derivados.excecoes}
                and not any(
                    _normalizar(item.nome) in {_normalizar(e) for e in lista.derivados.excecoes}
                    for item in lista.substancias
                    if nome in {_normalizar(n) for n in (item.nome, *item.sinonimos)}
                )
            )
            if candidatas:
                base = next(
                    item.nome
                    for item in candidatas[0].substancias
                    if nome in {_normalizar(n) for n in (item.nome, *item.sinonimos)}
                )
                return candidatas, base
        for texto, posicao, tipo in _FORMAS:
            restante = None
            if posicao == "prefixo" and nome.startswith(texto + " "):
                restante = nome[len(texto) + 1 :]
            elif posicao == "sufixo" and nome.endswith(" " + texto):
                restante = nome[: -len(texto) - 1]
            if restante:
                removidos = tipos_removidos | {tipo} if tipo != "hidratacao" else tipos_removidos
                pendentes.append((restante, removidos))
    return (), None


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
    """Compare nomes exatos e formas derivadas autorizadas pelos adendos."""
    consulta = _normalizar(substancia)
    encontradas = _INDICE.get(consulta, ())
    forma_base = None
    if not encontradas:
        encontradas, forma_base = _por_derivado(consulta)
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
        forma_base=forma_base,
        por_derivado=forma_base is not None,
    )
