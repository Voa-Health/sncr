from dataclasses import FrozenInstanceError

import pytest

from sncr import tipos


@pytest.mark.parametrize(
    "sigla,codigo,listas",
    [
        ("NRA", "1", ("A1", "A2", "A3")),
        ("NRB", "2", ("B1",)),
        ("NRB2", "3", ("B2",)),
        ("NRR", "4", ("C2",)),
        ("NRT", "5", ("C3",)),
        ("RCE", "6", ("C1", "C5")),
        ("RET", "7", ()),
    ],
)
def test_catalogo(sigla, codigo, listas):
    tipo = tipos.obter(sigla.lower())
    assert tipo.sigla == sigla
    assert tipo.codigo == codigo
    assert tipo.listas == listas
    assert tipos.por_codigo(codigo) is tipo
    assert tipos.por_codigo(int(codigo)) is tipo
    notificacao = int(codigo) <= 5
    assert tipo.exige_autorizacao_visa == notificacao
    assert tipo.familia == ("notificacao" if notificacao else "controle_especial")
    if notificacao:
        assert tipo.limites == tipos.Limites(
            por_requisicao_min=10, por_requisicao_max=50, por_dia=50
        )
    else:
        assert tipo.limites == tipos.Limites(
            por_requisicao=1000, requisicoes_por_mes=3, por_mes=3000
        )


def test_cores_e_listas():
    assert tipos.obter("NRA").cor == "amarela"
    assert tipos.obter("NRB").cor == "azul"
    assert all(tipos.obter(sigla).cor is None for sigla in ("NRB2", "NRR", "NRT", "RCE", "RET"))
    assert tipos.para_lista("a1") == (tipos.obter("NRA"),)
    assert tipos.para_lista("C5") == (tipos.obter("RCE"),)
    assert tipos.para_lista("C4") == ()
    assert tipos.para_lista("") == ()


@pytest.mark.parametrize("valor", ["", "xyz", "0", "8"])
def test_consulta_invalida(valor):
    with pytest.raises(ValueError, match="Sigla"):
        tipos.obter(valor)
    with pytest.raises(ValueError, match="Código"):
        tipos.por_codigo(valor)


def test_imutabilidade():
    with pytest.raises(TypeError):
        tipos.CATALOGO["XYZ"] = tipos.obter("NRA")
    with pytest.raises(FrozenInstanceError):
        tipos.obter("NRA").cor = "azul"
    with pytest.raises(FrozenInstanceError):
        tipos.obter("NRA").limites.por_dia = 1
    with pytest.raises(ValueError):
        tipos.Sigla("XYZ")
