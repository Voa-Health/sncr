import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import _cobertura
from scripts._manutencao_quality import _check_release_versions, _verificar_texto

ROOT = Path(__file__).resolve().parents[1]


def preparar(root):
    (root / "src/sncr").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    (root / "src/sncr/__init__.py").write_text('__version__ = "0.1.0"\n')
    dados = {
        "version": "0.1.0",
        "packages": [
            {
                "identifier": "sncr",
                "version": "0.1.0",
                "runtimeArguments": [{"name": "--with", "value": "sncr[mcp]==0.1.0"}],
            }
        ],
    }
    (root / "server.json").write_text(json.dumps(dados))
    return dados


def test_versoes_coerentes(tmp_path):
    preparar(tmp_path)
    assert _check_release_versions(tmp_path)


@pytest.mark.parametrize("campo", ["version", "packages", "pin", "vazio", "ausente"])
def test_versoes_divergentes(tmp_path, campo):
    dados = preparar(tmp_path)
    if campo == "version":
        dados["version"] = "0.2.0"
    elif campo == "packages":
        dados["packages"][0]["version"] = "0.2.0"
    elif campo == "pin":
        dados["packages"][0]["runtimeArguments"][0]["value"] = "sncr[mcp]==0.2.0"
    elif campo == "vazio":
        dados["packages"] = []
    else:
        dados["packages"][0]["runtimeArguments"] = []
    (tmp_path / "server.json").write_text(json.dumps(dados))
    assert not _check_release_versions(tmp_path)


def test_versao_python_divergente(tmp_path):
    preparar(tmp_path)
    (tmp_path / "src/sncr/__init__.py").write_text('__version__ = "0.2.0"\n')
    assert not _check_release_versions(tmp_path)


@pytest.mark.parametrize(
    "texto, permitido", [("", True), ("pacote público", True), ("\x23123", False)]
)
def test_conteudo(tmp_path, monkeypatch, texto, permitido):
    caminho = tmp_path / "README.md"
    caminho.write_text(texto)
    monkeypatch.setattr("scripts._manutencao_quality._arquivos", lambda root: [caminho])
    assert _verificar_texto(tmp_path) == permitido


@pytest.mark.parametrize("args", [["artefatos", "--check"]])
def test_comandos_offline(args):
    resultado = subprocess.run(
        [sys.executable, str(ROOT / "scripts/manutencao.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_comando_invalido():
    resultado = subprocess.run(
        [sys.executable, str(ROOT / "scripts/manutencao.py"), "invalido"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2


@pytest.mark.parametrize("encoding", ["utf-8-sig", "cp1252"])
def test_cobertura_csv(tmp_path, encoding):
    conteudo = (
        "SUBSTÂNCIA;APRESENTAÇÃO;TARJA\n"
        "CLONAZEPAM;Apresentação sintética A;Tarja Preta\n"
        "HEMITARTARATO DE ZOLPIDEM;Apresentação sintética B;Tarja Preta\n"
        '"ExemploInventado;MORFINA";Apresentação sintética C;Tarja Preta\n'
        "ExemploInventado;Apresentação sintética D;Sem tarja\n"
    ).encode(encoding)
    caminho = tmp_path / "sintetico.csv"
    caminho.write_bytes(conteudo)
    resultado = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/manutencao.py"),
            "cobertura",
            "--arquivo",
            str(caminho),
            "--url",
            "https://example.org/sintetico.csv",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "URL: https://example.org/sintetico.csv\nSHA256: " in resultado.stdout
    assert "Sem tarja\t1\t0\t0\t0.00\nTarja Preta\t3\t2\t3\t100.00\n" in resultado.stdout
    assert resultado.stdout == _cobertura.relatorio(conteudo, "https://example.org/sintetico.csv")
    for invalido in (b"", b"SUBSTANCIA;TARJA\nExemplo;Preta\n"):
        with pytest.raises(ValueError, match="colunas"):
            _cobertura.ler(invalido)


def test_cobertura_xlsx_e_download(monkeypatch):
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    buffer = BytesIO()
    with ZipFile(buffer, "w") as arquivo:
        arquivo.writestr(
            "xl/sharedStrings.xml",
            f'<sst xmlns="{namespace}">'
            "<si><t>SUBSTÂNCIA</t></si><si><t>TARJA</t></si>"
            "<si><t>APRESENTAÇÃO</t></si></sst>",
        )
        arquivo.writestr(
            "xl/worksheets/sheet1.xml",
            f'<worksheet xmlns="{namespace}">'
            '<sheetData><row r="1"><c r="A1" t="inlineStr"><is>'
            '<t>Título sintético</t></is></c></row><row r="3">'
            '<c r="A3" t="s"><v>0</v></c><c r="C3" t="s"><v>1</v></c>'
            '<c r="E3" t="s"><v>2</v></c></row><row r="4">'
            '<c r="A4" t="inlineStr"><is><t>ExemploInventado</t></is></c>'
            '<c r="E4" t="inlineStr"><is><t>Apresentação sintética</t></is></c>'
            "</row></sheetData></worksheet>",
        )
    conteudo = buffer.getvalue()
    assert _cobertura.ler(conteudo) == [
        {
            "SUBSTÂNCIA": "ExemploInventado",
            "TARJA": "",
            "APRESENTAÇÃO": "Apresentação sintética",
        }
    ]
    monkeypatch.setattr(
        _cobertura.urllib.request, "urlopen", lambda url, timeout: BytesIO(conteudo)
    )
    assert _cobertura.cobertura(None) == _cobertura.relatorio(conteudo)
    assert "(vazia)\t1\t0\t0\t0.00" in _cobertura.relatorio(conteudo)
