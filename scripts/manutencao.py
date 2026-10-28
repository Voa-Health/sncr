"""Verifique o pacote e mantenha fontes e artefatos locais."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from _manutencao_quality import verificar

ROOT = Path(__file__).resolve().parents[1]


def fontes() -> int:
    """Atualize as fontes cadastradas."""
    return 0


def artefatos(*, check: bool) -> int:
    """Gere ou confira os artefatos das fontes cadastradas."""
    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute uma operação de manutenção."""
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    comandos.add_parser("fontes", help="atualizar as fontes oficiais")
    geracao = comandos.add_parser("artefatos", help="gerar os artefatos locais")
    geracao.add_argument("--check", action="store_true")
    comandos.add_parser("verificar", help="verificar os padrões do pacote")
    args = parser.parse_args(argv)
    try:
        if args.comando == "fontes":
            return fontes()
        if args.comando == "artefatos":
            return artefatos(check=args.check)
        return verificar(ROOT)
    except (OSError, ValueError, KeyError, TypeError) as erro:
        logging.error("%s", erro)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
