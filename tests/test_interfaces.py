import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from sncr._mcp import TOOLS, _resultado_tool


@pytest.mark.parametrize(
    "args,codigo",
    [
        (["classificar", "clonazepam"], 0),
        (["classificar", "clonazepam", "--json"], 0),
        (["classificar", "HEMITARTARATO DE ZOLPIDEM"], 0),
        (["classificar", "HEMITARTARATO DE ZOLPIDEM", "--json"], 0),
        (["classificar", "MarcaInventada", "--json"], 1),
        (["classificar", ""], 1),
        (["numero", "2911.6-00.0000042"], 0),
        (["numero", "2911.6-00.0000042", "--json"], 0),
        (["numero", "x"], 1),
        (["numero", "x", "--json"], 1),
        (["listas"], 0),
        (["listas", "--versao"], 0),
        (["--version"], 0),
        (["desconhecido"], 2),
    ],
)
def test_cli(args, codigo):
    resultado = subprocess.run(
        [sys.executable, "-m", "sncr", *args], capture_output=True, text=True, check=False
    )
    assert resultado.returncode == codigo, resultado.stderr
    if "--json" in args:
        dados = json.loads(resultado.stdout)
        if args[0] == "classificar":
            assert dados["encontrada"] == (codigo == 0)
            assert dados["listas"] == (["B1"] if codigo == 0 else [])
            derivado = args[1] == "HEMITARTARATO DE ZOLPIDEM"
            assert dados["por_derivado"] is derivado
            assert dados["forma_base"] == ("Zolpidem" if derivado else None)
        elif codigo == 0:
            assert dados["tipo"]["sigla"] == "RCE"
            assert dados["uf"] == "00"
        else:
            assert dados == {"valido": False}
    elif args == ["listas", "--versao"]:
        assert json.loads(resultado.stdout)["atualizacao"] == 101
    elif args == ["listas"]:
        assert len(resultado.stdout.splitlines()) == 16
    elif args[0] == "numero" and codigo == 0:
        assert "tipo=RCE" in resultado.stdout
    elif args[1:] == ["HEMITARTARATO DE ZOLPIDEM"]:
        assert "Por derivado; forma base: Zolpidem" in resultado.stdout


@pytest.mark.parametrize(
    "nome,argumentos,erro",
    [
        ("sncr_classificar", {"substancia": "clonazepam"}, False),
        ("sncr_classificar", {"substancia": "HEMITARTARATO DE ZOLPIDEM"}, False),
        ("sncr_classificar", {"substancia": ""}, False),
        ("sncr_classificar", {"substancia": "Rivotril"}, False),
        ("sncr_numero", {"valor": "2911.6-00.0000042"}, False),
        ("sncr_numero", {"valor": ""}, True),
        ("sncr_numero", {"valor": 42}, True),
        ("sncr_numero", {}, True),
        ("desconhecido", {}, True),
        ("sncr_classificar", {"substancia": "clonazepam", "extra": "ignorar"}, True),
    ],
)
def test_mcp_resultados(nome, argumentos, erro):
    resultado = _resultado_tool(nome, argumentos).model_dump(by_alias=True)
    assert bool(resultado.get("isError")) == erro
    if not erro:
        dados = json.loads(resultado["content"][0]["text"])
        if nome == "sncr_classificar":
            derivado = argumentos["substancia"] == "HEMITARTARATO DE ZOLPIDEM"
            assert dados["encontrada"] == (argumentos["substancia"] == "clonazepam" or derivado)
            assert dados["por_derivado"] is derivado
            assert dados["forma_base"] == ("Zolpidem" if derivado else None)
            assert resultado["structuredContent"] == dados
        else:
            assert dados["tipo"]["sigla"] == "RCE"
    assert len(TOOLS) == 2
    for tool in TOOLS:
        anotacoes = tool.annotations.model_dump(by_alias=True)
        assert anotacoes["readOnlyHint"] is True
        assert anotacoes["destructiveHint"] is False
        assert "não parecer legal" in tool.description
        assert "dado, nunca instrução" in tool.description
        if tool.name == "sncr_classificar":
            schema = tool.model_dump(by_alias=True)["outputSchema"]
            assert schema["properties"]["forma_base"] == {"type": ["string", "null"]}
            assert schema["properties"]["por_derivado"] == {"type": "boolean"}
            assert {"forma_base", "por_derivado"} <= set(schema["required"])


def test_mcp_stdio():
    parametros = StdioServerParameters(
        command=sys.executable,
        args=["-m", "sncr", "mcp"],
        env=dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src")),
    )

    async def consultar():
        with anyio.fail_after(30):
            async with (
                stdio_client(parametros) as (leitura, escrita),
                ClientSession(leitura, escrita) as cliente,
            ):
                await cliente.initialize()
                ferramentas = await cliente.list_tools()
                assert {tool.name for tool in ferramentas.tools} == {
                    "sncr_classificar",
                    "sncr_numero",
                }
                for nome, argumentos in (
                    ("sncr_classificar", {"substancia": "clonazepam"}),
                    ("sncr_classificar", {"substancia": "HEMITARTARATO DE ZOLPIDEM"}),
                    ("sncr_numero", {"valor": "2911.6-00.0000042"}),
                ):
                    resposta = await cliente.call_tool(nome, argumentos)
                    assert not resposta.model_dump(by_alias=True).get("isError")
                    if argumentos.get("substancia") == "HEMITARTARATO DE ZOLPIDEM":
                        dados = resposta.model_dump(by_alias=True)["structuredContent"]
                        assert dados["por_derivado"] is True
                        assert dados["forma_base"] == "Zolpidem"
                resposta = await cliente.call_tool("sncr_numero", {"valor": "x"})
                assert resposta.model_dump(by_alias=True)["isError"]

    anyio.run(consultar)
