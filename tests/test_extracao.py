import hashlib
import importlib
import json
from pathlib import Path

import pytest

from scripts import _listas_data as dados

ROOT = Path(__file__).resolve().parents[1]
CONTAGENS = {
    "A1": 94,
    "A2": 13,
    "A3": 14,
    "B1": 95,
    "B2": 8,
    "C1": 213,
    "C2": 5,
    "C3": 3,
    "C5": 31,
    "D1": 35,
    "D2": 13,
    "E": 9,
    "F1": 56,
    "F2": 186,
    "F3": 1,
    "F4": 7,
}


def test_fonte_e_contagens():
    catalogo = json.loads(dados.compilar(ROOT))
    assert catalogo["fonte"]["atualizacao"] == 101
    assert catalogo["fonte"]["ato"] == dados.ATO
    assert set(catalogo["listas"]) == set(CONTAGENS)
    for sigla, contagem in CONTAGENS.items():
        regra = catalogo["listas"][sigla]["derivados"]
        assert regra["sais"] is (sigla != "D2")
        assert regra["isomeros"] is (sigla not in {"D1", "D2"})
        assert regra["esteres"] is (sigla not in {"C3", "D1", "D2", "F2", "F3", "F4"})
        assert regra["eteres"] == regra["esteres"]
        assert regra["excecoes"] == (["dextrometorfano", "dextrorfano"] if sigla == "A1" else [])
        itens = catalogo["listas"][sigla]["substancias"]
        assert len(itens) == contagem
        assert itens[-1]["numero"] == contagem
    assert (ROOT / dados.DESTINO).read_bytes() == dados.compilar(ROOT)
    assert (ROOT / dados.RELATORIO).read_bytes() == dados.relatorio(catalogo)
    assert all(
        "(Excluído)" not in item
        for lista in catalogo["listas"].values()
        for item in lista["adendos"]
    )
    assert any(
        "Portarias SVS/MS n.º 344/98 e 6/99" in item for item in catalogo["listas"]["E"]["adendos"]
    )
    assert any(
        "CLASSES ESTRUTURAIS DOS CANABINOIDES" in item
        for item in catalogo["listas"]["F2"]["adendos"]
    )


@pytest.mark.parametrize(
    "original,nome,sinonimos",
    [
        ("Dimefeptanol (metadol)", "Dimefeptanol", ["metadol"]),
        ("Ftalimidoglutarimida (talidomida)", "Ftalimidoglutarimida", ["talidomida"]),
        ("Canabidiol (CBD)", "Canabidiol", ["CBD"]),
        ("GHB - (ácido gama - hidroxibutírico)", "GHB", ["ácido gama - hidroxibutírico"]),
        (
            "N-(3-METIL-1-(FENETIL-4-PIPERIDIL)PROPIONANILIDA",
            "N-(3-METIL-1-(FENETIL-4-PIPERIDIL)PROPIONANILIDA",
            [],
        ),
        ("(+)3-metoxi", "(+)3-metoxi", []),
        (
            "MPPP ou 1-METIL-4-FENIL-4-PROPIONATO DE PIPERIDINA (ÉSTER)",
            "MPPP",
            ["1-METIL-4-FENIL-4-PROPIONATO DE PIPERIDINA (ÉSTER)"],
        ),
        (
            "2C-T-7 ou 2,5-DIMETOXI-4-PROPILTIOFENILETILAMINA (2C-T-7)",
            "2C-T-7",
            ["2,5-DIMETOXI-4-PROPILTIOFENILETILAMINA (2C-T-7)"],
        ),
        (
            "PARA-FLUOROBUTIRFENTANIL ou 4-FLUOROBUTIRILFENTANIL; 4F-BF; "
            "N- (4-FLUOROFENIL) -N- [1-(2-FENILETIL) PIPERIDIN-4-IL] BUTANAMIDA)",
            "PARA-FLUOROBUTIRFENTANIL",
            [
                "4-FLUOROBUTIRILFENTANIL",
                "4F-BF",
                "N- (4-FLUOROFENIL) -N- [1-(2-FENILETIL) PIPERIDIN-4-IL] BUTANAMIDA",
            ],
        ),
    ],
)
def test_sinonimos(original, nome, sinonimos):
    assert dados.substancia(original) == {"nome": nome, "sinonimos": sinonimos}


def test_blocos_e_fonte_invalida(tmp_path):
    html = b"<p>excetua-se nas \n<a>Portarias</a> e <strong>normas</strong>.</p>"
    assert dados.blocos(html) == ["excetua-se nas Portarias e normas."]
    with pytest.raises(ValueError, match="atualização"):
        dados.atualizacao(dados.blocos(b""))
    with pytest.raises(ValueError, match="Conjunto"):
        dados.extrair(b"")
    destino = tmp_path / dados.BRUTO
    destino.parent.mkdir(parents=True)
    destino.write_bytes((ROOT / dados.BRUTO).read_bytes() + b" ")
    (tmp_path / dados.METADADOS).write_bytes((ROOT / dados.METADADOS).read_bytes())
    with pytest.raises(ValueError, match="SHA-256"):
        dados.compilar(tmp_path)


def test_baixar_fonte(tmp_path, monkeypatch):
    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return (ROOT / dados.BRUTO).read_bytes()

    monkeypatch.setattr(dados.urllib.request, "urlopen", lambda url, timeout: Resposta())
    dados.atualizar(tmp_path)
    meta = json.loads((tmp_path / dados.METADADOS).read_bytes())
    assert meta["atualizacao"] == 101
    assert meta["sha256"] == hashlib.sha256((tmp_path / dados.BRUTO).read_bytes()).hexdigest()
    assert meta["url"] == dados.URL
    assert meta["data_obtencao"] == dados.date.today().isoformat()


def test_itens_separados_inline_e_adendos(monkeypatch):
    monkeypatch.setattr(dados, "SIGLAS", ("A1",))
    fonte = (
        "<div><p>LISTA - A1</p><p>Título</p><p>(Descrição)</p>"
        "<p>1.</p><p>Exemplo</p><p>ou</p><p>Alternativa</p>"
        "<p>2.Outro (Sinônimo)</p><p>ADENDO:</p><p>1) Ver "
        "<a>normas\ncomplementares</a>.</p><p>2) (Excluído)</p>"
        "<p>3) Outra regra.</p></div>"
    )
    lista = dados.extrair(fonte.encode("iso-8859-1"))["A1"]
    assert lista["descricao"] == "Descrição"
    assert [item["nome"] for item in lista["substancias"]] == ["Exemplo", "Outro"]
    assert lista["substancias"][0]["sinonimos"] == ["Alternativa"]
    assert lista["substancias"][1]["sinonimos"] == ["Sinônimo"]
    assert lista["adendos"] == ["1) Ver normas complementares.", "3) Outra regra."]


def test_artefatos_check_nao_escreve(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    cli = importlib.import_module("manutencao")
    esperado = dados.compilar(ROOT)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "compilar", lambda root: esperado)
    assert cli.artefatos(check=True) == 1
    assert not (tmp_path / dados.DESTINO).exists()
    assert cli.artefatos(check=False) == 0
    assert cli.artefatos(check=True) == 0
    (tmp_path / dados.DESTINO).write_bytes(b"{}")
    assert cli.artefatos(check=True) == 1
    assert (tmp_path / dados.DESTINO).read_bytes() == b"{}"


@pytest.mark.parametrize(
    "adendos,sais,esteres,excecoes",
    [
        ([], False, False, []),
        (["1) Padrões analíticos de sais e ésteres."], False, False, []),
        (
            ["1) ficam também sob controle todos os sais das substâncias desta Lista."],
            True,
            False,
            [],
        ),
        (
            [
                "1) ficam também sob controle os sais, ésteres e isômeros "
                "(exceto os isômeros exemplo, (+)3-metoxi, e o Outro, (+) 3-hidroxi), "
                "das substâncias enumeradas acima."
            ],
            True,
            True,
            ["exemplo", "outro"],
        ),
    ],
)
def test_extrair_derivados(adendos, sais, esteres, excecoes):
    regra = dados.derivados(adendos)
    assert regra["sais"] is sais
    assert regra["esteres"] is esteres
    assert regra["excecoes"] == excecoes
    with pytest.raises(ValueError, match="não reconhecido"):
        dados.derivados(["1) ficam também sob controle formas desconhecidas."])
