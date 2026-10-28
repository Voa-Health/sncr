from dataclasses import FrozenInstanceError, replace

import pytest

from sncr import fhir, listas, tipos


@pytest.mark.parametrize(
    "consulta,sigla,receituario",
    [
        ("clonazepam", "B1", "NRB"),
        ("morfina", "A1", "NRA"),
        ("metilfenidato", "A3", "NRA"),
        ("sibutramina", "B2", "NRB2"),
        ("fluoxetina", "C1", "RCE"),
        ("isotretinoína", "C2", "NRR"),
        ("isotretinoina", "C2", "NRR"),
        ("  ISOTRETINOÍNA ", "C2", "NRR"),
        ("talidomida", "C3", "NRT"),
    ],
)
def test_classificar(consulta, sigla, receituario):
    resultado = listas.classificar(consulta)
    assert resultado.consulta == consulta
    assert resultado.encontrada
    assert resultado.listas == (sigla,)
    assert resultado.receituarios == (tipos.obter(receituario),)
    assert resultado.pendencias == listas.lista(sigla).adendos
    assert resultado.fonte.atualizacao == 101
    assert resultado.fonte.ato == "RDC nº 1.036, de 09/07/2026"
    assert not resultado.por_derivado
    assert resultado.forma_base is None


@pytest.mark.parametrize(
    "consulta", ["", " \t\n ", "Rivotril", "MarcaInventadaExemplo", "clonaze", "clonazepam extra"]
)
def test_nao_encontrada(consulta):
    resultado = listas.classificar(consulta)
    assert not resultado.encontrada
    assert resultado.listas == resultado.receituarios == resultado.pendencias == ()


@pytest.mark.parametrize("sigla", ["D1", "E", "F1", "F2", "F3", "F4"])
def test_sem_receituario(sigla):
    lista = listas.lista(sigla)
    resultado = listas.classificar(lista.substancias[0].nome)
    assert resultado.encontrada
    assert sigla in resultado.listas
    assert not resultado.receituarios
    assert (lista.descricao or lista.titulo) in resultado.pendencias
    assert all(adendo in resultado.pendencias for adendo in lista.adendos)


def test_normalizacao_e_sinonimos():
    resultado = listas.classificar("  HIDRATO \t DE\n CLORAL ")
    assert resultado.encontrada
    assert listas.classificar("isotretinoi\u0301na").listas == ("C2",)
    assert listas.classificar("4F-BF").listas == ("F1",)
    assert not listas.classificar("ÉSTER").encontrada
    assert listas.classificar("2,5-DIMETOXI-4-PROPILTIOFENILETILAMINA (2C-T-7)").listas == ("F2",)


def test_catalogo_imutavel_e_invalido():
    assert len(listas.listas()) == 16
    assert listas.lista(" b1 ") is listas.lista("B1")
    with pytest.raises(ValueError, match="desconhecida"):
        listas.lista("C4")
    with pytest.raises(FrozenInstanceError):
        listas.lista("B1").titulo = "alterado"
    resultado = listas.classificar("clonazepam")
    with pytest.raises(FrozenInstanceError):
        resultado.encontrada = False
    with pytest.raises(FrozenInstanceError):
        resultado.fonte.atualizacao = 0
    with pytest.raises(FrozenInstanceError):
        listas.lista("B1").substancias[0].nome = "alterado"


def test_multiplas_listas_e_mesmo_receituario(monkeypatch):
    item = listas.Substancia(1, "Exemplo (alternativa)", "Exemplo", ("alternativa", "EXEMPLO"))
    catalogo = tuple(
        replace(listas.lista(sigla), substancias=(item,)) for sigla in ("A1", "A3", "B1")
    )
    monkeypatch.setattr(listas, "_INDICE", listas._indexar(catalogo))
    resultado = listas.classificar("alternativa")
    assert resultado.listas == ("A1", "A3", "B1")
    assert resultado.receituarios == (tipos.obter("NRA"), tipos.obter("NRB"))
    assert resultado.pendencias == tuple(a for lista in catalogo for a in lista.adendos)
    assert listas.classificar("Exemplo").listas == resultado.listas


@pytest.mark.parametrize(
    "consulta,sigla,base,receituario",
    [
        ("HEMITARTARATO DE ZOLPIDEM", "B1", "ZOLPIDEM", "NRB"),
        ("CLORIDRATO DE METILFENIDATO", "A3", "METILFENIDATO", "NRA"),
        ("SULFATO DE MORFINA PENTAIDRATADO", "A1", "MORFINA", "NRA"),
    ],
)
def test_formas_derivadas(consulta, sigla, base, receituario):
    resultado = listas.classificar(consulta)
    assert resultado.listas == (sigla,)
    assert resultado.receituarios == (tipos.obter(receituario),)
    assert resultado.forma_base.casefold() == base.casefold()
    assert resultado.por_derivado


def test_derivados_nao_encontrados():
    assert not listas.classificar("losartana").encontrada
    for consulta in (
        "BROMIDRATO DE DEXTROMETORFANO",
        "CLORIDRATO DE LOSARTANA",
        "CLORIDRATO DE " + listas.lista("D2").substancias[0].nome,
    ):
        resultado = listas.classificar(consulta)
        assert not resultado.encontrada
        assert not resultado.por_derivado
        assert resultado.forma_base is None


@pytest.mark.parametrize(
    "consulta,sigla,excecoes,esperado",
    [
        ("cloridrato de exemplo", "A1", (), True),
        ("cloridrato de alternativa", "A1", ("Exemplo",), False),
        ("cloridrato de exemplo", "A1", ("exemplo",), False),
        ("cloridrato de exemplo", "D2", (), False),
        ("decanoato de exemplo", "D1", (), False),
        ("cloridrato de decanoato de exemplo pentaidratado", "A1", (), True),
        ("cloridrato de decanoato de exemplo", "D1", (), False),
        ("exemplo anidro", "D2", (), True),
        ("exemplo sodico", "A1", (), True),
        ("", "A1", (), False),
    ],
)
def test_derivado_sintetico(monkeypatch, consulta, sigla, excecoes, esperado):
    item = listas.Substancia(1, "Exemplo", "Exemplo", ("alternativa",))
    lista = replace(
        listas.lista(sigla),
        substancias=(item,),
        derivados=replace(listas.lista(sigla).derivados, excecoes=excecoes),
    )
    monkeypatch.setattr(listas, "_INDICE", listas._indexar((lista,)))
    encontradas, base = listas._por_derivado(consulta)
    assert bool(encontradas) is esperado
    assert base == ("Exemplo" if esperado else None)


@pytest.mark.parametrize(
    "principios,siglas",
    [
        (["clonazepam", "morfina", "SubstanciaInventada"], ["A1", "B1"]),
        (["clonazepam", "zolpidem"], ["B1"]),
        (["HEMITARTARATO DE ZOLPIDEM"], ["B1"]),
        (["SubstanciaInventada"], ["sem-lista"]),
        ([], []),
        (["", " \t"], []),
        (["", "SubstanciaInventada"], ["sem-lista"]),
        ([listas.lista("D2").substancias[0].nome], ["D2"]),
    ],
)
def test_categorias_fhir(principios, siglas):
    categorias = fhir.categorias(iter(principios))
    assert [categoria["coding"][0]["code"] for categoria in categorias] == siglas
    for categoria, sigla in zip(categorias, siglas, strict=True):
        if sigla == "sem-lista":
            assert categoria == {
                "coding": [
                    {
                        "system": "https://github.com/Voa-Health/sncr/lista",
                        "version": "101",
                        "code": "sem-lista",
                        "display": "Fora das listas da Portaria 344",
                    }
                ],
                "text": "Fora das listas da Portaria 344",
            }
            continue
        lista = listas.lista(sigla)
        classificacao = listas.classificar(lista.substancias[0].nome)
        assert categoria == {
            "coding": [
                {
                    "system": "https://github.com/Voa-Health/sncr/lista",
                    "version": "101",
                    "code": sigla,
                    "display": lista.titulo,
                },
                *[
                    {
                        "system": "https://github.com/Voa-Health/sncr/receituario",
                        "version": "101",
                        "code": tipo.sigla,
                        "display": tipo.nome,
                    }
                    for tipo in tipos.para_lista(sigla)
                ],
            ],
            "text": f"Portaria SVS/MS 344/98, Atualização nº 101: Lista {sigla}; "
            + "; ".join(classificacao.pendencias),
        }
