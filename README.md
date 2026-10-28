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
instalam dependências opcionais. CLI e consultas offline não carregam o cliente HTTP.

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

## Listas de substâncias

```python
from sncr import listas

resultado = listas.classificar("clonazepam")
assert resultado.listas == ("B1",)
assert resultado.receituarios[0].sigla == "NRB"
assert listas.classificar("Rivotril").encontrada is False
```

A consulta tenta primeiro nomes e sinônimos exatos, ignorando acentos, maiúsculas
e espaços repetidos. Não identifica nomes comerciais nem aproximações.
Sem correspondência exata, remove iterativamente prefixos e sufixos da
[tabela de formas](src/sncr/data/derivados.json) até encontrar uma forma-base.
Só aceita o derivado quando o adendo de **"ficam também sob controle"** da lista
estende o controle a todos os tipos removidos: sal, éster ou éter.
Hidratação é neutra e não exige extensão adicional. Exceções nomeadas bloqueiam
derivados, como dextrometorfano e dextrorfano em A1. D2 não tem extensão a sais.

O resultado inclui atualização e ato de origem, `por_derivado` e `forma_base`.
Esta última preserva o nome da norma e é `None` em consultas exatas ou não encontradas.

```python
resultado = listas.classificar("HEMITARTARATO DE ZOLPIDEM")
assert resultado.listas == ("B1",)
assert resultado.por_derivado is True
assert resultado.forma_base == "Zolpidem"
```

A classificação não substitui a leitura da norma. Os adendos são devolvidos em
`pendencias` para revisão humana; somente as regras gerais de derivados são aplicadas.
Correspondência nominal não decide exceções por forma farmacêutica ou concentração:
elas ficam em `pendencias`. Listas sem receituário SNCR também devolvem a descrição
do cabeçalho como pendência.
Uma consulta não encontrada não significa receita simples ou ausência de controle.
O catálogo pode ser lido com `listas.listas()` e `listas.lista("B1")`.

### Categorias FHIR R5

`sncr.fhir.categorias(principios)` gera elementos de `MedicationRequest.category`,
um por lista, deduplicados e na ordem da Portaria. Cada elemento inclui os codings
de lista e receituário, com códigos `str` e a atualização da norma em `version`.
O `text` é curto: identifica a lista, sinaliza a existência de adendos e, quando
aplicável, a ausência de receituário de controle associado. O texto integral dos
adendos continua disponível em `Classificacao.pendencias`, sem alterações.
Princípios vazios são ignorados; entrada vazia gera `[]`.

Exemplo sintético de princípio não encontrado, com saída JSON completa e curta:

```python
import json
from sncr import fhir

print(json.dumps(fhir.categorias(["SubstanciaInventada"]), ensure_ascii=False, indent=2))
```

```json
[
  {
    "coding": [
      {
        "system": "https://github.com/Voa-Health/sncr/lista",
        "version": "101",
        "code": "sem-lista",
        "display": "Fora das listas da Portaria 344"
      }
    ],
    "text": "Fora das listas da Portaria 344"
  }
]
```

`sem-lista` significa ausência de correspondência no catálogo, não parecer de
ausência de controle. Para princípios encontrados, os sistemas são
`https://github.com/Voa-Health/sncr/lista` e
`https://github.com/Voa-Health/sncr/receituario`.

### Cobertura CMED

Medição em **28/10/2026** sobre a planilha oficial PF/PMC de **09/10/2026**,
[arquivo de referência](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/precos/arquivos/lista_pmc__20261009_115232672.xlsx/@@download/file).
Uma apresentação casa quando **algum** princípio casa; compostos são separados
por `;`. A coluna com derivados inclui as correspondências exatas.

| Tarja publicada | Apresentações | Exato | Com derivados | Cobertura |
| --- | ---: | ---: | ---: | ---: |
| `- (*)` | 4.610 | 248 | 459 | 9,96% |
| Tarja Preta | 740 | 243 | 740 | 100,00% |
| Tarja Sem Tarja | 1.836 | 0 | 39 | 2,12% |
| Tarja Vermelha | 13.928 | 290 | 450 | 3,23% |
| Tarja Vermelha sob restrição | 5.521 | 1.842 | 3.888 | 70,42% |

Tarja preta: **740/740** com derivados, das quais **243** já casavam exato.
Isso mede correspondência nominal, não valida a tarja ou o receituário da apresentação.
As 39 apresentações sem tarja correspondentes também exigem revisão das pendências.
A planilha não é empacotada; o relatório registra URL e SHA-256.

```sh
uv run python scripts/manutencao.py cobertura
uv run python scripts/manutencao.py cobertura --arquivo caminho/planilha.xlsx
```

- [Fontes de dados](DATA_SOURCES.md)
- [Contribuição](CONTRIBUTING.md)
- [Segurança](SECURITY.md)

## Cliente HTTP opcional

```sh
pip install "sncr[cliente]"
```

```python
import os
from sncr import tipos
from sncr.cliente import Cliente

with Cliente("homologacao", os.environ["SNCR_BEARER"]) as cliente:
    # Utilize somente um prescritor de teste autorizado no ambiente.
    resultado = cliente.numerar_notificacao(
        tipos.obter("NRA"), "CRM", "SP", os.environ["SNCR_DOCUMENTO_TESTE"], 10
    )
```

O ambiente é obrigatório. **O cliente não faz login gov.br, não guarda token
e não repete requisições.** A credencial fica apenas na memória da conexão;
não há persistência em arquivo. Encerre a conexão com `with` ou `close()`.
O extra instala somente `httpx`.

`ErroDeConexao` representa falha antes do envio; repetir é seguro.
`ResultadoIncerto` significa que números podem ter sido consumidos: reconcilie
o resultado com o serviço antes de qualquer nova tentativa. Isso inclui falhas
de leitura/escrita, respostas inesperadas e confirmação fora do contrato.
Redirecionamentos são recusados sem reenviar o bearer.
Erros 400 expõem a mensagem da API, sem inferir sua causa por texto;
401, 403 e 404 têm exceções específicas, todas derivadas de `ErroSncr`.

Para RCE/RET use `numerar_controle_especial(tipo, conselho, uf, documento, cnpj)`,
com `jws_integradora=` opcional no header `X-Jws-Integradora`.
O CNPJ deve ter 14 dígitos e verificadores válidos. Não envie dados de teste
à produção. O logger `sncr.cliente` registra somente operação, status e duração.

## Linha de comando

```sh
sncr classificar clonazepam
sncr classificar "isotretinoína" --json
sncr numero 2602.6-53.0000001 --json
sncr listas
sncr listas --versao
```

`classificar` retorna código 0 quando encontra a designação, 1 quando não;
`numero` retorna 1 para entrada inválida. A consulta é offline, não acessa
o cliente e não confirma emissão ou validade legal. Use `--json` para ler
os componentes completos e, na classificação, os textos das pendências.
Uma correspondência nominal não é parecer legal.

## MCP local

```sh
pip install "sncr[mcp]"
sncr mcp
```

Servidor stdio, com suporte às duas versões maiores do SDK MCP:
`sncr_classificar(substancia)` e `sncr_numero(valor)`. São duas ferramentas
somente de leitura, sem conexão com o cliente HTTP ou serviço remoto.
As respostas representam correspondência nominal ou validação estrutural,
não parecer legal. O texto de entrada é dado, nunca instrução.
O manifesto `server.json` fixa o extra na mesma versão do pacote.

## Licença

Apache-2.0. Consulte [LICENSE](LICENSE).
