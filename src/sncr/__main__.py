"""Interface offline de linha de comando."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from sncr import __version__, listas, numero


def _emitir(dados: Any) -> None:
    sys.stdout.write(json.dumps(dados, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    """Execute consultas offline ou inicie o servidor MCP em stdio."""
    parser = argparse.ArgumentParser(prog="sncr")
    parser.add_argument("--version", action="version", version=__version__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    for nome, campo in (("classificar", "substancia"), ("numero", "valor")):
        comando = comandos.add_parser(nome)
        comando.add_argument(campo)
        comando.add_argument("--json", action="store_true")
    catalogo = comandos.add_parser("listas")
    catalogo.add_argument("--versao", action="store_true")
    comandos.add_parser("mcp", help="iniciar o servidor MCP offline em stdio")
    args = parser.parse_args(argv)
    if args.comando == "mcp":
        try:
            from sncr._mcp import main as iniciar
        except ImportError:
            sys.stderr.write('Instale o extra MCP: pip install "sncr[mcp]"\n')
            return 2
        iniciar()
        return 0
    if args.comando == "classificar":
        resultado = listas.classificar(args.substancia)
        if args.json:
            _emitir(asdict(resultado))
        else:
            sys.stdout.write(
                ", ".join(resultado.listas) + "\n" if resultado.encontrada else "Não encontrada.\n"
            )
            if resultado.encontrada:
                sys.stdout.write(
                    f"Revisão humana: {len(resultado.pendencias)} pendências; "
                    "use --json para os textos completos.\n"
                )
        return 0 if resultado.encontrada else 1
    if args.comando == "numero":
        try:
            dados = asdict(numero.decompor(args.valor))
        except ValueError:
            if args.json:
                _emitir({"valido": False})
            else:
                sys.stderr.write("Numeração inválida.\n")
            return 1
        if args.json:
            _emitir(dados)
        else:
            sys.stdout.write(numero.formatar(args.valor) + "\n")
            sys.stdout.write(
                f"ano={dados['ano']:02d} mes={dados['mes']:02d} tipo={dados['tipo']['sigla']} "
                f"uf={dados['uf']} sequencial={dados['sequencial']} digitos={dados['digitos']} "
                f"prefixo={dados['prefixo']}\n"
            )
        return 0
    if args.versao:
        _emitir(asdict(listas.classificar("").fonte))
    else:
        for lista in listas.listas():
            sys.stdout.write(f"{lista.sigla}: {lista.titulo}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
