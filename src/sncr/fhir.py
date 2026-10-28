"""Categorias FHIR R5 de medicamentos segundo as listas da Portaria 344."""

from collections.abc import Iterable
from typing import Any

from sncr import listas, tipos

SISTEMA_LISTA = "https://github.com/Voa-Health/sncr/lista"
SISTEMA_RECEITUARIO = "https://github.com/Voa-Health/sncr/receituario"
_FORA = "Fora das listas da Portaria 344"


def categorias(principios: Iterable[str]) -> list[dict[str, Any]]:
    """Produza MedicationRequest.category, sem inferir autorização de prescrição."""
    encontradas: set[str] = set()
    fonte = None
    for principio in principios:
        if not principio.strip():
            continue
        resultado = listas.classificar(principio)
        fonte = resultado.fonte
        encontradas.update(resultado.listas)
    if fonte is None:
        return []
    versao = str(fonte.atualizacao)
    if not encontradas:
        return [
            {
                "coding": [
                    {
                        "system": SISTEMA_LISTA,
                        "version": versao,
                        "code": "sem-lista",
                        "display": _FORA,
                    }
                ],
                "text": _FORA,
            }
        ]
    categorias: list[dict[str, Any]] = []
    for lista in listas.listas():
        if lista.sigla not in encontradas:
            continue
        associados = tipos.para_lista(lista.sigla)
        codings = [
            {
                "system": SISTEMA_LISTA,
                "version": versao,
                "code": lista.sigla,
                "display": lista.titulo,
            }
        ]
        codings.extend(
            {
                "system": SISTEMA_RECEITUARIO,
                "version": versao,
                "code": tipo.sigla.value,
                "display": tipo.nome,
            }
            for tipo in associados
        )
        texto = f"Portaria SVS/MS 344/98, Atualização nº {versao}: Lista {lista.sigla}"
        if lista.adendos:
            texto += " (sujeita aos adendos da lista)"
        if not associados:
            texto += " — sem receituário de controle associado"
        categorias.append({"coding": codings, "text": texto})
    return categorias
