Pacote Python sobre receituários de medicamentos controlados da Anvisa (SNCR — Sistema Nacional de Controle de Receituários).

# sncr

O projeto não tem vínculo com a Anvisa nem com o Ministério da Saúde.
A classificação não substitui a leitura da norma.

## Instalação

Requer Python 3.11 ou superior.

```sh
pip install sncr
```

O pacote base não possui dependências de execução. Os extras `cliente` e `mcp`
instalam dependências opcionais. Não há interface de linha de comando nem servidor MCP.

```python
import sncr

assert sncr.__version__ == "0.1.0"
```

- [Fontes de dados](DATA_SOURCES.md)
- [Contribuição](CONTRIBUTING.md)
- [Segurança](SECURITY.md)

## Licença

Apache-2.0. Consulte [LICENSE](LICENSE).
