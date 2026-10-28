from dataclasses import FrozenInstanceError
from types import GeneratorType

import pytest

from sncr import numero, tipos


@pytest.mark.parametrize("tamanho", [14, 16])
@pytest.mark.parametrize("codigo", "1234567")
def test_numero(tamanho, codigo):
    sequencial = "0" * (tamanho - 9) + "42"
    digitos = f"2911{codigo}00{sequencial}"
    pontuado = f"2911.{codigo}-00.{sequencial}"
    assert numero.normalizar(f"  {pontuado}  ") == digitos
    assert numero.valido(digitos)
    assert numero.formatar(digitos) == pontuado
    partes = numero.decompor(pontuado)
    assert partes.ano == 29
    assert partes.mes == 11
    assert partes.tipo is tipos.por_codigo(codigo)
    assert partes.uf == "00"
    assert partes.sequencial == 42
    assert partes.digitos == tamanho
    assert partes.prefixo == f"2911{codigo}00"
    with pytest.raises(FrozenInstanceError):
        partes.mes = 1


@pytest.mark.parametrize(
    "valor",
    [
        None,
        "",
        " ",
        "123",
        "2911600000004",
        "291160000000420",
        "29116000000042000",
        "2911600000004x",
        "2911/6-00.0000042",
        "\uff12" * 14,
    ],
)
def test_normalizacao_invalida(valor):
    assert numero.normalizar(valor) is None
    assert not numero.valido(valor)
    with pytest.raises(ValueError, match="inválida"):
        numero.formatar(valor)
    with pytest.raises(ValueError, match="inválida"):
        numero.decompor(valor)


@pytest.mark.parametrize("prefixo", ["2900600", "2913600", "2911000", "2911800"])
def test_mes_tipo_invalidos(prefixo):
    valor = prefixo + "0000042"
    assert numero.normalizar(valor) == valor
    assert not numero.valido(valor)
    with pytest.raises(ValueError):
        numero.formatar(valor)


@pytest.mark.parametrize("mes", ["01", "12"])
def test_zero_e_limites_mes(mes):
    partes = numero.decompor(f"00{mes}7990000000")
    assert partes.ano == 0
    assert partes.uf == "99"
    assert partes.sequencial == 0
    assert numero.valido(f"00{mes}799" + "0" * 9)


def test_faixa_documentada():
    intervalo = numero.faixa("2602.6-53.0000001", "2602.6-53.0001000")
    assert len(intervalo) == 1000
    assert intervalo.inicio == "2602.6-53.0000001"
    assert intervalo.fim == "2602.6-53.0001000"
    assert "26026530000500" in intervalo
    assert "2602.6-53.0000500" in intervalo
    assert "26026530001001" not in intervalo
    assert "26026540000500" not in intervalo
    assert "26026530000000" not in intervalo
    assert "" not in intervalo
    assert "inválido" not in intervalo
    assert None not in intervalo
    assert "2602653000000500" not in intervalo
    gerador = iter(intervalo)
    assert isinstance(gerador, GeneratorType)
    assert next(gerador) == intervalo.inicio
    ultimo = None
    for valor in gerador:
        ultimo = valor
    assert ultimo == intervalo.fim


@pytest.mark.parametrize("tamanho", [14, 16])
def test_faixa_sintetica(tamanho):
    inicio = "2911600" + str(42).zfill(tamanho - 7)
    fim = "2911600" + str(44).zfill(tamanho - 7)
    intervalo = numero.faixa(inicio, fim)
    assert len(intervalo) == 3
    assert list(intervalo) == [
        numero.formatar("2911600" + str(n).zfill(tamanho - 7)) for n in range(42, 45)
    ]
    assert len(numero.faixa(inicio, inicio)) == 1
    with pytest.raises(FrozenInstanceError):
        intervalo.inicio = fim


@pytest.mark.parametrize(
    "inicio,fim",
    [
        ("", "2911.6-00.0000044"),
        ("2911.6-00.0000042", ""),
        ("2911.6-00.0000044", "2911.6-00.0000042"),
        ("2911.6-00.0000042", "2911.6-01.0000044"),
        ("2911.6-00.0000042", "2912.6-00.0000044"),
        ("2911.6-00.0000042", "2911.7-00.0000044"),
        ("2911.6-00.0000042", "3011.6-00.0000044"),
        ("2911.6-00.0000042", "2911.6-00.000000044"),
    ],
)
def test_faixa_invalida(inicio, fim):
    with pytest.raises(ValueError):
        numero.faixa(inicio, fim)
