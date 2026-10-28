"""Catálogo de receituários e limites de obtenção de numerações SNCR."""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Literal


class Sigla(StrEnum):
    """Siglas dos sete tipos de receituário SNCR."""

    NRA = "NRA"
    NRB = "NRB"
    NRB2 = "NRB2"
    NRR = "NRR"
    NRT = "NRT"
    RCE = "RCE"
    RET = "RET"


@dataclass(frozen=True)
class Limites:
    """Cotas da API: diárias por tipo/prescritor; mensais por inscrição profissional."""

    por_requisicao_min: int | None = None
    por_requisicao_max: int | None = None
    por_dia: int | None = None
    por_requisicao: int | None = None
    requisicoes_por_mes: int | None = None
    por_mes: int | None = None


@dataclass(frozen=True)
class Tipo:
    """Tipo de receituário e suas características normativas."""

    sigla: Sigla
    nome: str
    codigo: str
    familia: Literal["notificacao", "controle_especial"]
    cor: str | None
    listas: tuple[str, ...]
    exige_autorizacao_visa: bool
    limites: Limites


_NOTIFICACAO = Limites(por_requisicao_min=10, por_requisicao_max=50, por_dia=50)
_CONTROLE = Limites(por_requisicao=1000, requisicoes_por_mes=3, por_mes=3000)
CATALOGO = MappingProxyType(
    {
        Sigla.NRA: Tipo(
            Sigla.NRA,
            'Notificação de Receita "A"',
            "1",
            "notificacao",
            "amarela",
            ("A1", "A2", "A3"),
            True,
            _NOTIFICACAO,
        ),
        Sigla.NRB: Tipo(
            Sigla.NRB,
            'Notificação de Receita "B"',
            "2",
            "notificacao",
            "azul",
            ("B1",),
            True,
            _NOTIFICACAO,
        ),
        Sigla.NRB2: Tipo(
            Sigla.NRB2,
            'Notificação de Receita "B2"',
            "3",
            "notificacao",
            None,
            ("B2",),
            True,
            _NOTIFICACAO,
        ),
        Sigla.NRR: Tipo(
            Sigla.NRR,
            "Notificação de Receita Especial para Retinóides de Uso Sistêmico",
            "4",
            "notificacao",
            None,
            ("C2",),
            True,
            _NOTIFICACAO,
        ),
        Sigla.NRT: Tipo(
            Sigla.NRT,
            "Notificação de Receita Especial para Talidomida",
            "5",
            "notificacao",
            None,
            ("C3",),
            True,
            _NOTIFICACAO,
        ),
        Sigla.RCE: Tipo(
            Sigla.RCE,
            "Receita de Controle Especial",
            "6",
            "controle_especial",
            None,
            ("C1", "C5"),
            False,
            _CONTROLE,
        ),
        Sigla.RET: Tipo(
            Sigla.RET,
            "Receita sujeita a Retenção",
            "7",
            "controle_especial",
            None,
            (),
            False,
            _CONTROLE,
        ),
    }
)


def obter(sigla: str) -> Tipo:
    """Obtenha um tipo pela sigla, sem distinguir maiúsculas de minúsculas."""
    try:
        return CATALOGO[Sigla(sigla.upper())]
    except ValueError:
        raise ValueError(f"Sigla de receituário desconhecida: {sigla!r}") from None


def por_codigo(digito: str | int) -> Tipo:
    """Obtenha um tipo pelo código de um dígito."""
    for tipo in CATALOGO.values():
        if tipo.codigo == str(digito):
            return tipo
    raise ValueError(f"Código de receituário desconhecido: {digito!r}")


def para_lista(lista: str) -> tuple[Tipo, ...]:
    """Retorne os tipos associados à sigla de uma lista, ou uma tupla vazia."""
    return tuple(tipo for tipo in CATALOGO.values() if lista.upper() in tipo.listas)
