"""Verifique o pacote e mantenha fontes e artefatos locais."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from _cobertura import URL, cobertura
from _listas_data import DESTINO, RELATORIO, atualizar, compilar, relatorio
from _manutencao_quality import verificar

ROOT = Path(__file__).resolve().parents[1]


def fontes() -> int:
    """Atualize as fontes cadastradas."""
    atualizar(ROOT)
    return 0


def artefatos(*, check: bool) -> int:
    """Gere ou confira os artefatos das fontes cadastradas."""
    esperado = compilar(ROOT)
    arquivos = ((DESTINO, esperado), (RELATORIO, relatorio(json.loads(esperado))))
    for caminho, conteudo in arquivos:
        destino = ROOT / caminho
        if check:
            if not destino.is_file() or destino.read_bytes() != conteudo:
                logging.error("Artefato desatualizado: %s", caminho)
                return 1
        else:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(conteudo)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute uma operação de manutenção."""
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("fontes", help="atualizar as fontes oficiais")
    geracao = comandos.add_parser("artefatos", help="gerar os artefatos locais")
    geracao.add_argument("--check", action="store_true")
    comandos.add_parser("verificar", help="verificar os padrões do pacote")
    medicao = comandos.add_parser("cobertura", help="medir correspondência na CMED")
    medicao.add_argument("--arquivo", "--csv", type=Path)
    medicao.add_argument("--url", default=URL, help="URL de origem registrada no relatório")
    args = parser.parse_args(argv)
    try:
        if args.comando == "fontes":
            return fontes()
        if args.comando == "artefatos":
            return artefatos(check=args.check)
        if args.comando == "cobertura":
            sys.stdout.write(cobertura(args.arquivo, args.url))
            return 0
        return verificar(ROOT)
    except (OSError, ValueError, KeyError, TypeError) as erro:
        logging.error("%s", erro)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
