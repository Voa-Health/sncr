import json
import subprocess
import sys
from pathlib import Path

import pytest

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
