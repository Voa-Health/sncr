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

A consulta compara somente nomes e sinônimos exatos, ignorando acentos,
maiúsculas e espaços repetidos. Não identifica nomes comerciais nem aproximações.
O resultado inclui a atualização e o ato de origem.

A classificação não substitui a leitura da norma. Os adendos são devolvidos em
`pendencias` para revisão humana; não são aplicados automaticamente. Listas sem
receituário SNCR também devolvem a descrição do cabeçalho como pendência.
Uma consulta não encontrada não significa receita simples ou ausência de controle.
O catálogo pode ser lido com `listas.listas()` e `listas.lista("B1")`.

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
