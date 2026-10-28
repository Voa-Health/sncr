"""Cliente de numeração sem login, armazenamento persistente de token ou repetição."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal

import httpx

from sncr import numero, tipos

_BASES = {
    "producao": "https://api-gateway.prd.apps.anvisa.gov.br/api-sncr",
    "homologacao": "https://api-gateway.hmg.apps.anvisa.gov.br/api-sncr",
}
_UFS = frozenset(
    [
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    ]
)
_LOG = logging.getLogger(__name__)


class ErroSncr(Exception):
    """Erro seguro da operação de numeração."""


class ErroDeConexao(ErroSncr):
    """Falha antes do envio; repetir a operação é seguro."""


class ResultadoIncerto(ErroSncr):
    """A numeração pode ter sido consumida; não repita sem reconciliação."""


class RedirecionamentoRecusado(ErroSncr):
    """Redirecionamento recusado sem reenviar credenciais."""


class RequisicaoRecusada(ErroSncr):
    """Requisição recusada pela API, sem interpretação textual da causa."""


class NaoAutenticado(ErroSncr):
    """Credencial não aceita pela API."""


class SemPermissao(ErroSncr):
    """Operação não permitida pela API."""


class NaoEncontrado(ErroSncr):
    """Recurso não encontrado pela API."""


@dataclass(frozen=True)
class Notificacoes:
    """Números e saldo retornados pela API."""

    numeros: tuple[str, ...]
    saldo: int
    mensagem: str


@dataclass(frozen=True)
class ControleEspecial:
    """Faixa inclusiva confirmada pela API."""

    faixa: numero.Faixa
    quantidade: int
    mensagem: str


def _cnpj_valido(valor: str) -> bool:
    if (
        not isinstance(valor, str)
        or len(valor) != 14
        or not valor.isascii()
        or not valor.isdecimal()
    ):
        return False
    if len(set(valor)) == 1:
        return False
    base = valor[:12]
    for pesos in ((5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2), (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)):
        resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) % 11
        base += str(0 if resto < 2 else 11 - resto)
    return base == valor


def _validar(uf: str, documento: str) -> None:
    if not isinstance(uf, str) or uf not in _UFS:
        raise ValueError("UF deve ser uma das 27 siglas brasileiras.")
    if not isinstance(documento, str) or not documento.strip():
        raise ValueError("Documento não pode ser vazio.")


def _mensagem(dados: Any, nivel: int = 0) -> str:
    if nivel > 5:
        return ""
    if isinstance(dados, dict):
        for campo in ("mensagem", "description"):
            if isinstance(dados.get(campo), str):
                return str(dados[campo])
        return _mensagem(dados.get("errorObject"), nivel + 1)
    if isinstance(dados, list):
        return "; ".join(filter(None, (_mensagem(item, nivel + 1) for item in dados)))
    return ""


class Cliente:
    """Conexão explícita ao ambiente escolhido, sem repetição de requisições."""

    def __init__(
        self,
        ambiente: Literal["homologacao", "producao"],
        bearer: str,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if ambiente not in _BASES:
            raise ValueError("Ambiente deve ser homologacao ou producao.")
        self._bearer = bearer
        self._http = httpx.Client(
            base_url=_BASES[ambiente],
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            headers={"Authorization": f"Bearer {bearer}"},
        )

    def __enter__(self) -> Cliente:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        """Feche os recursos da conexão."""
        self._http.close()

    def _limpar(self, mensagem: str, jws: str | None) -> str:
        for segredo in sorted(filter(None, (self._bearer, jws)), key=len, reverse=True):
            mensagem = mensagem.replace(segredo, "[redigido]")
        return mensagem

    def _post(self, op: str, corpo: dict[str, Any], jws: str | None = None) -> Any:
        inicio = perf_counter()
        status: int | None = None
        try:
            try:
                resposta = self._http.post(
                    f"/api/v1/numeracoes/{op}",
                    json=corpo,
                    headers={"X-Jws-Integradora": jws} if jws is not None else {},
                )
            except (httpx.ConnectError, httpx.ConnectTimeout):
                raise ErroDeConexao("Conexão não estabelecida; repetir é seguro.") from None
            except httpx.TransportError:
                raise ResultadoIncerto("Resultado incerto; não repita automaticamente.") from None
            status = resposta.status_code
            if 300 <= status < 400:
                raise RedirecionamentoRecusado("Redirecionamento recusado.")
            if status in (401, 403, 404):
                erro = {401: NaoAutenticado, 403: SemPermissao, 404: NaoEncontrado}[status]
                raise erro("Operação recusada pela API.")
            if status == 400:
                try:
                    mensagem = _mensagem(resposta.json())
                except ValueError:
                    mensagem = ""
                raise RequisicaoRecusada(
                    self._limpar(mensagem or "Requisição recusada pela API.", jws)
                )
            if status != 201:
                raise ResultadoIncerto(
                    "Resposta sem confirmação válida; reconcilie antes de repetir."
                )
            try:
                return resposta.json()
            except ValueError:
                raise ResultadoIncerto("Resposta de numeração inválida.") from None
        finally:
            _LOG.info(
                "op=%s status=%s duracao_ms=%.3f", op, status, (perf_counter() - inicio) * 1000
            )

    def numerar_notificacao(
        self,
        receita: tipos.Tipo,
        conselho: str,
        uf: str,
        documento: str,
        quantidade: int = 50,
    ) -> Notificacoes:
        """Solicite notificações uma única vez, validando os números retornados."""
        _validar(uf, documento)
        if not isinstance(receita, tipos.Tipo) or receita.familia != "notificacao":
            raise ValueError("Receita deve pertencer à família notificacao.")
        if type(quantidade) is not int or not 10 <= quantidade <= 50:
            raise ValueError("Quantidade deve ser um inteiro de 10 a 50.")
        dados = self._post(
            "notificacao-receita",
            {
                "receita": receita.sigla,
                "conselho": conselho,
                "uf": uf,
                "documento": documento,
                "quantidade": quantidade,
            },
        )
        try:
            valores = dados["numeracoesReceita"]
            if not isinstance(valores, list) or not valores:
                raise ValueError
            if type(dados["saldoReceitas"]) is not int or not isinstance(dados["mensagem"], str):
                raise ValueError
            for valor in valores:
                if not isinstance(valor, str) or numero.decompor(valor).tipo != receita:
                    raise ValueError
            return Notificacoes(tuple(valores), dados["saldoReceitas"], dados["mensagem"])
        except (KeyError, TypeError, ValueError):
            raise ResultadoIncerto("Resposta de notificação inválida.") from None

    def numerar_controle_especial(
        self,
        tipo: tipos.Tipo,
        conselho: str,
        uf: str,
        documento: str,
        cnpj: str,
        *,
        jws_integradora: str | None = None,
    ) -> ControleEspecial:
        """Solicite RCE ou RET uma única vez, conferindo faixa, tipo e quantidade."""
        _validar(uf, documento)
        if not isinstance(tipo, tipos.Tipo) or tipo.sigla not in (tipos.Sigla.RCE, tipos.Sigla.RET):
            raise ValueError("Tipo deve ser RCE ou RET.")
        if not _cnpj_valido(cnpj):
            raise ValueError("CNPJ deve conter 14 dígitos e verificadores válidos.")
        dados = self._post(
            "receita-especial-retencao",
            {
                "conselho": conselho,
                "tipo": tipo.sigla,
                "documento": documento,
                "uf": uf,
                "cnpj": cnpj,
            },
            jws_integradora,
        )
        try:
            if not isinstance(dados["inicio"], str) or not isinstance(dados["fim"], str):
                raise ValueError
            intervalo = numero.Faixa(dados["inicio"], dados["fim"])
            if numero.decompor(intervalo.inicio).tipo != tipo:
                raise ValueError
            if type(dados["quantidade"]) is not int or dados["quantidade"] != len(intervalo):
                raise ValueError
            if not isinstance(dados["mensagem"], str):
                raise ValueError
            return ControleEspecial(intervalo, dados["quantidade"], dados["mensagem"])
        except (KeyError, TypeError, ValueError):
            raise ResultadoIncerto("Resposta de controle especial inválida.") from None
