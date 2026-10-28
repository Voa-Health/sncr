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

## Tipos e numerações

Exemplo com numeração sintética, sem vínculo com prescritor:

```python
from sncr import numero, tipos

assert tipos.obter("nra").codigo == "1"
assert tipos.para_lista("C1") == (tipos.obter("RCE"),)
assert numero.formatar("29116000000042") == "2911.6-00.0000042"
assert len(numero.faixa("2911.6-00.0000042", "2911.6-00.0000044")) == 3
```

A validação é estrutural: não consulta emissão, titularidade ou situação no SNCR.
Aceita 14 e 16 dígitos e não aplica dígito verificador. UF é mantida como texto,
sem associação com códigos IBGE. Veja limites e fontes em [DATA_SOURCES.md](DATA_SOURCES.md).

- [Fontes de dados](DATA_SOURCES.md)
- [Contribuição](CONTRIBUTING.md)
- [Segurança](SECURITY.md)

## Licença

Apache-2.0. Consulte [LICENSE](LICENSE).
