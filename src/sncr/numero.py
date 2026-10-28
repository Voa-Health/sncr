"""Normalização e validação estrutural de numerações SNCR, sem dígito verificador."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal

from sncr import tipos

_SEPARADORES = re.compile(r"[.\-\s]")


def normalizar(valor: str | None) -> str | None:
    """Remova pontos, hífens e espaços e aceite 14 ou 16 dígitos ASCII."""
    digitos = _SEPARADORES.sub("", valor or "")
    if len(digitos) not in (14, 16) or not digitos.isascii() or not digitos.isdecimal():
        return None
    return digitos


def valido(valor: str | None) -> bool:
    """Confira comprimento, mês e tipo, sem impor restrições à UF ou ao sequencial."""
    digitos = normalizar(valor)
    return digitos is not None and 1 <= int(digitos[2:4]) <= 12 and digitos[4] in "1234567"


@dataclass(frozen=True)
class Numero:
    """Componentes de uma numeração; ano é o inteiro aa, sem inferência de século."""

    ano: int
    mes: int
    tipo: tipos.Tipo
    uf: str
    sequencial: int
    digitos: Literal[14, 16]
    prefixo: str


def decompor(valor: str) -> Numero:
    """Decomponha uma numeração válida preservando UF e prefixo como texto."""
    digitos = normalizar(valor)
    if digitos is None or not valido(digitos):
        raise ValueError(f"Numeração SNCR inválida: {valor!r}")
    return Numero(
        ano=int(digitos[:2]),
        mes=int(digitos[2:4]),
        tipo=tipos.por_codigo(digitos[4]),
        uf=digitos[5:7],
        sequencial=int(digitos[7:]),
        digitos=14 if len(digitos) == 14 else 16,
        prefixo=digitos[:7],
    )


def formatar(valor: str) -> str:
    """Pontue AAMM.T-UU.sequencial; não há exemplo oficial pontuado de 16 dígitos."""
    numero = decompor(valor)
    prefixo = numero.prefixo
    sequencial = f"{numero.sequencial:0{numero.digitos - 7}d}"
    return f"{prefixo[:4]}.{prefixo[4]}-{numero.uf}.{sequencial}"


@dataclass(frozen=True)
class Faixa:
    """Intervalo inclusivo com extremos formatados e iteração sem materialização."""

    inicio: str
    fim: str

    def __post_init__(self) -> None:
        primeiro = decompor(self.inicio)
        ultimo = decompor(self.fim)
        if primeiro.prefixo != ultimo.prefixo or primeiro.digitos != ultimo.digitos:
            raise ValueError("Os extremos devem ter o mesmo prefixo e número de dígitos.")
        if primeiro.sequencial > ultimo.sequencial:
            raise ValueError("O início da faixa deve ser menor ou igual ao fim.")
        object.__setattr__(self, "inicio", formatar(self.inicio))
        object.__setattr__(self, "fim", formatar(self.fim))

    def __len__(self) -> int:
        return decompor(self.fim).sequencial - decompor(self.inicio).sequencial + 1

    def __contains__(self, valor: object) -> bool:
        if not isinstance(valor, str) or not valido(valor):
            return False
        numero = decompor(valor)
        inicio = decompor(self.inicio)
        fim = decompor(self.fim)
        return (
            numero.prefixo == inicio.prefixo
            and numero.digitos == inicio.digitos
            and inicio.sequencial <= numero.sequencial <= fim.sequencial
        )

    def __iter__(self) -> Iterator[str]:
        inicio = decompor(self.inicio)
        fim = decompor(self.fim)
        for sequencial in range(inicio.sequencial, fim.sequencial + 1):
            yield formatar(f"{inicio.prefixo}{sequencial:0{inicio.digitos - 7}d}")


def faixa(inicio: str, fim: str) -> Faixa:
    """Crie uma faixa inclusiva de mesmo prefixo e comprimento, em ordem crescente."""
    return Faixa(inicio, fim)
