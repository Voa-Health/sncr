import json
import logging
import subprocess
import sys
import traceback
from dataclasses import FrozenInstanceError

import httpx
import pytest

from sncr import tipos
from sncr.cliente import (
    Cliente,
    ErroDeConexao,
    NaoAutenticado,
    NaoEncontrado,
    RedirecionamentoRecusado,
    RequisicaoRecusada,
    ResultadoIncerto,
    SemPermissao,
    _cnpj_valido,
)

NRA = tipos.obter("NRA")
RCE = tipos.obter("RCE")
CNPJ = "12333333000111"
SEGREDO = "s" * 16
JWS = "j" * 16
NOTIFICACAO = {
    "numeracoesReceita": ["2911.1-00.0000042"],
    "saldoReceitas": 49,
    "mensagem": "Disponibilizado",
}
CONTROLE = {
    "inicio": "2911.6-00.0000042",
    "fim": "2911.6-00.0000044",
    "quantidade": 3,
    "mensagem": "Disponibilizado",
}


def chamar(cliente, controle=False, **kwargs):
    if controle:
        return cliente.numerar_controle_especial(
            kwargs.pop("tipo", RCE), "CRM", "SP", "sintetico", CNPJ, **kwargs
        )
    return cliente.numerar_notificacao(NRA, "CRM", "SP", "sintetico", **kwargs)


@pytest.mark.parametrize("controle", [False, True])
@pytest.mark.parametrize("ambiente", ["homologacao", "producao"])
@pytest.mark.parametrize("jws", [None, JWS])
@pytest.mark.parametrize("sigla", ["RCE", "RET"])
def test_contrato(controle, ambiente, jws, sigla):
    pedidos = []

    def responder(request):
        pedidos.append(request)
        corpo = {
            **CONTROLE,
            "inicio": CONTROLE["inicio"].replace(".6-", f".{tipos.obter(sigla).codigo}-"),
            "fim": CONTROLE["fim"].replace(".6-", f".{tipos.obter(sigla).codigo}-"),
        }
        return httpx.Response(201, json=corpo if controle else NOTIFICACAO)

    with Cliente(ambiente, SEGREDO, transport=httpx.MockTransport(responder)) as cliente:
        resultado = chamar(
            cliente,
            controle,
            **({"jws_integradora": jws, "tipo": tipos.obter(sigla)} if controle else {}),
        )
    assert len(pedidos) == 1
    request = pedidos[0]
    host = "p" + "rd" if ambiente == "producao" else "hmg"
    op = "receita-especial-retencao" if controle else "notificacao-receita"
    assert (
        str(request.url)
        == f"https://api-gateway.{host}.apps.anvisa.gov.br/api-sncr/api/v1/numeracoes/{op}"
    )
    corpo = {"conselho": "CRM", "documento": "sintetico", "uf": "SP"}
    corpo.update(
        {"tipo": sigla, "cnpj": CNPJ} if controle else {"receita": "NRA", "quantidade": 50}
    )
    assert json.loads(request.content) == corpo
    assert request.headers["Authorization"] == f"Bearer {SEGREDO}"
    assert request.headers.get("X-Jws-Integradora") == (jws if controle else None)
    assert request.extensions["timeout"]["read"] == 30.0
    if controle:
        assert resultado.quantidade == len(resultado.faixa) == 3
    else:
        assert resultado.numeros == tuple(NOTIFICACAO["numeracoesReceita"])
        assert resultado.saldo == 49
    with pytest.raises(FrozenInstanceError):
        resultado.mensagem = "alterado"


@pytest.mark.parametrize("controle", [False, True])
@pytest.mark.parametrize(
    "status,erro",
    [
        (400, RequisicaoRecusada),
        (401, NaoAutenticado),
        (403, SemPermissao),
        (404, NaoEncontrado),
        (301, RedirecionamentoRecusado),
        (302, RedirecionamentoRecusado),
        (307, RedirecionamentoRecusado),
        (308, RedirecionamentoRecusado),
        (200, ResultadoIncerto),
        (202, ResultadoIncerto),
        (204, ResultadoIncerto),
        (429, ResultadoIncerto),
        (500, ResultadoIncerto),
        (502, ResultadoIncerto),
    ],
)
def test_status_sem_repeticao(controle, status, erro):
    pedidos = []

    def responder(request):
        pedidos.append(request)
        return httpx.Response(status, headers={"Location": "https://example.invalid/"})

    with (
        Cliente("homologacao", SEGREDO, transport=httpx.MockTransport(responder)) as cliente,
        pytest.raises(erro),
    ):
        chamar(cliente, controle)
    assert len(pedidos) == 1


@pytest.mark.parametrize("controle", [False, True])
@pytest.mark.parametrize(
    "falha,erro",
    [(httpx.ConnectError, ErroDeConexao), (httpx.ConnectTimeout, ErroDeConexao)]
    + [
        (falha, ResultadoIncerto)
        for falha in (
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.PoolTimeout,
        )
    ],
)
def test_transporte_e_segredos(controle, falha, erro, caplog):
    pedidos = []

    def responder(request):
        pedidos.append(request)
        raise falha(SEGREDO + JWS, request=request)

    with (
        caplog.at_level(logging.INFO, logger="sncr.cliente"),
        Cliente("homologacao", SEGREDO, transport=httpx.MockTransport(responder)) as cliente,
    ):
        with pytest.raises(erro) as capturado:
            chamar(cliente, controle, **({"jws_integradora": JWS} if controle else {}))
        texto = str(capturado.value) + repr(capturado.value) + repr(cliente) + str(cliente)
        texto += "".join(traceback.format_exception(capturado.value))
    assert len(pedidos) == 1
    assert SEGREDO not in texto + caplog.text
    assert JWS not in texto + caplog.text
    assert "sintetico" not in caplog.text
    assert CNPJ not in caplog.text
    assert "status=" in caplog.text and "duracao_ms=" in caplog.text


@pytest.mark.parametrize(
    "payload,mensagem",
    [
        ({"codigo": "RECUSADO", "mensagem": "Limite"}, "Limite"),
        ([{"mensagem": "Primeira"}, {"mensagem": "Segunda"}], "Primeira; Segunda"),
        ({"errorObject": {"description": "Descrição"}}, "Descrição"),
        ({"mensagem": SEGREDO + JWS}, "[redigido][redigido]"),
        ({"mensagem": 1}, "Requisição recusada pela API."),
        (None, "Requisição recusada pela API."),
    ],
)
def test_mensagens_recusadas(payload, mensagem):
    transport = httpx.MockTransport(lambda request: httpx.Response(400, json=payload))
    with (
        Cliente("homologacao", SEGREDO, transport=transport) as cliente,
        pytest.raises(RequisicaoRecusada) as erro,
    ):
        chamar(cliente, True, jws_integradora=JWS)
    assert str(erro.value) == mensagem


@pytest.mark.parametrize(
    "controle,payload",
    [
        (False, {}),
        (False, []),
        (False, None),
        (False, "invalid-json"),
        (True, "invalid-json"),
        (False, {**NOTIFICACAO, "numeracoesReceita": []}),
        (False, {**NOTIFICACAO, "numeracoesReceita": "não é lista"}),
        (False, {**NOTIFICACAO, "numeracoesReceita": ["inválido"]}),
        (False, {**NOTIFICACAO, "numeracoesReceita": ["2911.2-00.0000042"]}),
        (False, {**NOTIFICACAO, "saldoReceitas": True}),
        (False, {**NOTIFICACAO, "mensagem": None}),
        (True, {}),
        (True, None),
        (True, {**CONTROLE, "quantidade": 4}),
        (True, {**CONTROLE, "quantidade": True}),
        (True, {**CONTROLE, "inicio": "inválido"}),
        (True, {**CONTROLE, "fim": "2911.7-00.0000044"}),
        (True, {**CONTROLE, "inicio": "2911.7-00.0000042", "fim": "2911.7-00.0000044"}),
        (True, {**CONTROLE, "mensagem": []}),
    ],
)
def test_schema_invalido(controle, payload):
    pedidos = []

    def responder(request):
        pedidos.append(request)
        if payload == "invalid-json":
            return httpx.Response(201, content=b"not json")
        return httpx.Response(201, json=payload)

    with (
        Cliente("homologacao", SEGREDO, transport=httpx.MockTransport(responder)) as cliente,
        pytest.raises(ResultadoIncerto),
    ):
        chamar(cliente, controle)
    assert len(pedidos) == 1


@pytest.mark.parametrize("controle", [False, True])
@pytest.mark.parametrize(
    "campo,valor",
    [
        ("uf", "XX"),
        ("uf", None),
        ("documento", "  "),
        ("documento", None),
        ("tipo", NRA),
        ("receita", RCE),
        ("tipo", None),
        ("receita", None),
        ("quantidade", 9),
        ("quantidade", 51),
        ("quantidade", True),
        ("cnpj", "0" * 14),
        ("cnpj", CNPJ[:-1] + "0"),
        ("cnpj", "123"),
        ("cnpj", None),
    ],
)
def test_validacao_local(controle, campo, valor):
    if (controle and campo in {"receita", "quantidade"}) or (
        not controle and campo in {"tipo", "cnpj"}
    ):
        return
    pedidos = []
    transport = httpx.MockTransport(pedidos.append)
    kwargs = {"conselho": "CRM", "uf": "SP", "documento": "sintetico"}
    kwargs.update({"tipo": RCE, "cnpj": CNPJ} if controle else {"receita": NRA})
    kwargs[campo] = valor
    with (
        Cliente("homologacao", SEGREDO, transport=transport) as cliente,
        pytest.raises(ValueError),
    ):
        metodo = cliente.numerar_controle_especial if controle else cliente.numerar_notificacao
        metodo(**kwargs)
    assert pedidos == []
    assert _cnpj_valido(CNPJ)


def test_importacao_sem_httpx():
    resultado = subprocess.run(
        [sys.executable, "-c", "import sys; import sncr; assert 'httpx' not in sys.modules"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
