<div align="center">
  <h1>sncr</h1>
  <h3>Receituários de medicamentos controlados, para pessoas e agentes de IA.</h3>
</div>

<div align="center">
  <a href="https://github.com/Voa-Health/sncr/actions/workflows/ci.yml"><img src="https://github.com/Voa-Health/sncr/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/sncr/"><img src="https://img.shields.io/pypi/v/sncr?label=PyPI" alt="Versão no PyPI"></a>
  <a href="https://pypi.org/project/sncr/"><img src="https://img.shields.io/pypi/pyversions/sncr" alt="Versões do Python"></a>
  <a href="https://github.com/Voa-Health/sncr/blob/main/LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-Apache--2.0-blue" alt="Licença Apache-2.0"></a>
</div>

<div align="center">
  <a href="#início-rápido">Início rápido</a> ·
  <a href="#cli">CLI</a> ·
  <a href="#conectar-agentes">MCP local</a> ·
  <a href="#referência">Referência</a> ·
  <a href="https://github.com/Voa-Health/sncr/blob/main/DATA_SOURCES.md">Fontes de dados</a>
</div>

<br>

Consulte substâncias nas listas da Portaria SVS/MS nº 344/1998, encontre os tipos
de receituário associados e confira a estrutura de numerações do Sistema Nacional
de Controle de Receituários (SNCR). Uma biblioteca Python em código aberto, com
CLI e MCP locais, além de um cliente opcional para a API de numeração da Anvisa.

> [!IMPORTANT]
> O projeto não tem vínculo com a Anvisa nem com o Ministério da Saúde.
> A classificação não substitui a leitura da norma. Validar a estrutura de um
> número não confirma emissão, titularidade ou situação no SNCR.

> [!TIP]
> Usa Claude Code, Codex ou Cursor? Conecte o MCP local e peça, por exemplo,
> "consulte clonazepam e mostre as pendências para revisão". Veja
> [Conectar agentes](#conectar-agentes).

## Início rápido

Requer Python 3.11+. O pacote base não possui dependências de execução.

```sh
pip install sncr
```

```python
from sncr import listas

resultado = listas.classificar("clonazepam")
assert resultado.listas == ("B1",)
assert resultado.receituarios[0].sigla == "NRB"
assert resultado.pendencias
```

O resultado traz as listas encontradas, os receituários associados, a fonte e os
adendos em `pendencias`, para revisão humana. Uma consulta não encontrada
**não significa receita simples ou ausência de controle**.

## Acesso e limites

A biblioteca offline, a CLI e o MCP locais não têm cota de uso.
O MCP hospedado em `https://api.voa.health/mcp/sncr/` aceita
`Authorization: Bearer <chave>` com chave de organização (`sk_voa_`) ou de
membro (`sk_user_`), com escopo `sncr:read`, criada no
[console](https://tiss-api.voa.health/org), ou OAuth.

A cota diária por organização é compartilhada entre Terminologia, RNDS e SNCR,
por chave e OAuth: 1.000 consultas com login, 10.000 para organizações
verificadas; organizações pessoais Pro/Trial/Ultra não têm limite.
Ao exceder a cota, HTTP `429` informa `retry_after` quando disponível e um link
para o console (o cabeçalho `Retry-After` também pode estar presente).
Quando a cobrança estiver habilitada, HTTP `402` traz
`error_name: "PAYMENT_REQUIRED"` e `metadata.billing_url` para pagamento.
Consulte os preços públicos via
[`GET /api/v2/product/sncr/pricing/`](https://api.voa.health/api/v2/product/sncr/pricing/).

## CLI

Instale com `pip install sncr` ou execute sem instalar com
`uvx sncr classificar clonazepam`.

| Comando | Uso |
| --- | --- |
| `sncr classificar clonazepam` | Consulta uma substância e informa quantas pendências exigem revisão. |
| `sncr classificar "isotretinoína" --json` | Retorna a classificação com os textos completos das pendências. |
| `sncr numero 2911.6-00.0000042 --json` | Decompõe uma numeração sintética, sem confirmar emissão. |
| `sncr listas` | Lista siglas e títulos do catálogo. |
| `sncr listas --versao` | Mostra os metadados da fonte normativa em JSON. |
| `sncr --version` | Mostra a versão instalada do pacote. |
| `sncr mcp` | Inicia o MCP local em stdio; requer `sncr[mcp]`. |

`classificar` retorna `0` quando encontra a designação e `1` quando não encontra;
`numero` retorna `1` para entrada inválida. Erros de uso retornam `2`.
As consultas rodam offline e não carregam o cliente HTTP. Use `--json` em
`classificar` e `numero` para obter os campos completos.

## Para quem é

| Você é | O sncr ajuda a |
| --- | --- |
| **Desenvolvedor de sistemas de prescrição** | consultar listas, associar receituários e gerar categorias FHIR R5 |
| **Profissional de saúde ou farmacêutico** | localizar designações na norma e os adendos que precisam de leitura |
| **Integrador da API SNCR** | solicitar numerações com ambiente explícito e tratar respostas incertas |
| **Desenvolvedor de agentes de IA** | oferecer consultas locais, somente de leitura, por MCP |

## Como funciona

1. **Consulte** o princípio ativo com `listas.classificar`.
2. **Confira** as listas e os receituários associados no resultado.
3. **Revise** os adendos em `pendencias`, inclusive exceções por concentração ou
   forma farmacêutica. O pacote não decide essas exceções.
4. **Trate a numeração separadamente:** `numero` confere a estrutura local;
   obter números no serviço da Anvisa exige o cliente opcional e autenticação.

A busca compara nomes e sinônimos exatos, ignorando acentos, maiúsculas e espaços
repetidos. Sem correspondência, tenta formas derivadas autorizadas pelos adendos.
Não busca nomes comerciais, aproximações ou equivalência química por estrutura.

## O que vem no pacote

- **[Biblioteca Python](#referência):** listas de substâncias, tipos de
  receituário, numerações, faixas inclusivas e categorias FHIR R5.
- **[CLI](#cli):** consultas offline, com saída em texto ou JSON.
- **[MCP local](#conectar-agentes):** duas ferramentas somente de leitura,
  sem acesso ao cliente HTTP.
- **[Cliente HTTP opcional](#cliente-http-opcional):** obtenção de numerações
  de notificação e de receita de controle especial ou sujeita a retenção.
- **[Fontes de dados](https://github.com/Voa-Health/sncr/blob/main/DATA_SOURCES.md):**
  documentos oficiais, hashes e método de reprodução do catálogo.

## Por que confiar

- **Consultas offline e determinísticas:** o catálogo vai no pacote; consultar
  substâncias e decompor números não exige rede.
- **Fontes rastreáveis:** o catálogo inclui ato e atualização de origem; a
  extração usa uma fonte local conferida por SHA-256.
- **Limites explícitos:** correspondência nominal não é parecer legal e os
  adendos permanecem disponíveis para revisão humana.
- **Rede opcional:** somente o cliente de numeração faz chamadas à API SNCR;
  ele não repete requisições nem segue redirecionamentos.

## Conectar agentes

O [pacote ChatGPT](plugins/chatgpt/) conecta o serviço remoto autenticado via OAuth
para consultar apenas substâncias com `sncr_classificar`, sem dados pessoais e sem
operações de numeração. É distribuído separadamente do wheel Python.

O MCP local roda em stdio e oferece duas ferramentas:

| Ferramenta | Uso |
| --- | --- |
| `sncr_classificar(substancia)` | Consulta nomes, sinônimos e derivados nas listas da norma. |
| `sncr_numero(valor)` | Decompõe uma numeração, sem confirmar emissão. |

No Claude Code:

```sh
claude mcp add sncr -- uvx --from "sncr[mcp]" sncr mcp
```

Para instalar e iniciar diretamente:

```sh
pip install "sncr[mcp]"
sncr mcp
```

As ferramentas são somente de leitura. As respostas representam correspondência
nominal ou validação estrutural, não parecer legal. O texto de entrada é dado,
nunca instrução. Agentes encontram as orientações do repositório em
[AGENTS.md](https://github.com/Voa-Health/sncr/blob/main/AGENTS.md).

### Codex e Cursor

<details>
<summary>Ver configuração</summary>

No Codex, adicione a `~/.codex/config.toml`:

```toml
[mcp_servers.sncr]
command = "uvx"
args = ["--from", "sncr[mcp]", "sncr", "mcp"]
```

No Cursor, adicione ao `mcp.json`:

```json
{
  "mcpServers": {
    "sncr": {
      "command": "uvx",
      "args": ["--from", "sncr[mcp]", "sncr", "mcp"]
    }
  }
}
```

</details>

### Privacidade

Biblioteca base, CLI de consulta e MCP local não enviam dados à rede nem
telemetria. O MCP não acessa o cliente de numeração. Ao usar o cliente HTTP,
os dados da solicitação são enviados ao ambiente da Anvisa escolhido
explicitamente; o logger `sncr.cliente` registra apenas operação, status e duração.

## Cliente HTTP opcional

```sh
pip install "sncr[cliente]"
```

O extra instala `httpx`. `Cliente` exige o ambiente (`homologacao` ou `producao`)
e um bearer do prescritor. **Não faz login gov.br, não persiste o token em arquivo
e não repete requisições.** Feche a conexão com `with` ou `close()`.

Exemplo inteiramente sintético, com transporte simulado e **sem chamada de rede**:

```python
import httpx

from sncr import tipos
from sncr.cliente import Cliente


def simular(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        201,
        json={
            "numeracoesReceita": [f"2911100{n:07d}" for n in range(42, 52)],
            "saldoReceitas": 40,
            "mensagem": "Exemplo sintético",
        },
    )


with Cliente("homologacao", "token-sintetico", transport=httpx.MockTransport(simular)) as cliente:
    resultado = cliente.numerar_notificacao(tipos.obter("NRA"), "CRM", "SP", "TESTE", 10)
    assert len(resultado.numeros) == 10
```

Para uma integração com o serviço, consulte os requisitos e endpoints nas
[fontes de dados](https://github.com/Voa-Health/sncr/blob/main/DATA_SOURCES.md#endpoints-de-integração).
Use somente prescritor de teste autorizado em homologação. Não envie dados
sintéticos à produção.

Para RCE/RET, use
`numerar_controle_especial(tipo, conselho, uf, documento, cnpj)`, com
`jws_integradora=` opcional no header `X-Jws-Integradora`. O CNPJ precisa ter
14 dígitos e verificadores válidos. O retorno confere tipo, faixa e quantidade.

### Falhas e repetição

- `ErroDeConexao`: falha antes do envio; repetir é seguro.
- `ResultadoIncerto`: números podem ter sido consumidos. Reconcilie o resultado
  com o serviço antes de qualquer nova tentativa.
- `RedirecionamentoRecusado`: o bearer não é reenviado a outro endereço.
- `RequisicaoRecusada`: erro 400 com mensagem da API, sem inferir a causa pelo texto.
- `NaoAutenticado`, `SemPermissao` e `NaoEncontrado`: respostas 401, 403 e 404.

Todas derivam de `ErroSncr`. Falhas de leitura ou escrita, respostas inesperadas
e confirmações fora do contrato podem resultar em `ResultadoIncerto`.

## Referência

### Símbolos da biblioteca

| Símbolo | Uso |
| --- | --- |
| `listas.classificar(substancia)` | Retorna listas, receituários, fonte e pendências. |
| `listas.listas()` / `listas.lista(sigla)` | Consulta o catálogo de listas na ordem da norma ou uma lista pela sigla. |
| `tipos.obter(sigla)` / `tipos.por_codigo(digito)` | Consulta um tipo de receituário. |
| `tipos.para_lista(sigla)` | Retorna os tipos associados a uma lista. |
| `numero.normalizar(valor)` / `numero.valido(valor)` | Normaliza dígitos ou verifica a estrutura. |
| `numero.decompor(valor)` / `numero.formatar(valor)` | Decompõe ou pontua uma numeração. |
| `numero.faixa(inicio, fim)` | Cria um intervalo inclusivo, iterável sem materializar todos os números. |
| `fhir.categorias(principios)` | Gera elementos de `MedicationRequest.category` do FHIR R5. |

### Classificação e derivados

<details>
<summary>Ver regras e limites</summary>

Sem correspondência exata, a consulta remove iterativamente prefixos e sufixos
da [tabela de formas](https://github.com/Voa-Health/sncr/blob/main/src/sncr/data/derivados.json)
até encontrar uma forma-base. Só aceita o derivado quando o adendo de
**"ficam também sob controle"** estende o controle a todos os tipos removidos:
sal, éster ou éter. Hidratação é neutra e não exige extensão adicional.

Exceções nomeadas bloqueiam derivados, como dextrometorfano e dextrorfano em A1.
A lista D2 não tem extensão a sais. Somente as regras gerais de derivados são
aplicadas; exceções por apresentação, concentração ou forma farmacêutica
permanecem em `pendencias`. Listas sem receituário SNCR também devolvem a
descrição do cabeçalho como pendência.

```python
from sncr import listas

resultado = listas.classificar("HEMITARTARATO DE ZOLPIDEM")
assert resultado.listas == ("B1",)
assert resultado.por_derivado is True
assert resultado.forma_base == "Zolpidem"
assert listas.classificar("Rivotril").encontrada is False
```

`forma_base` preserva o nome da norma e é `None` em consultas exatas ou não
encontradas. A fonte em `resultado.fonte` informa a atualização e o ato de origem.
O catálogo é uma cópia versionada: a consulta não verifica mudanças na norma
pela rede. Consulte também o
[relatório de extração](https://github.com/Voa-Health/sncr/blob/main/docs/extracao.md).

</details>

### Tipos e numerações

<details>
<summary>Ver exemplo e limites estruturais</summary>

Exemplo com numeração sintética, sem vínculo com prescritor:

```python
from sncr import numero, tipos

assert tipos.obter("nra").codigo == "1"
assert tipos.para_lista("C1") == (tipos.obter("RCE"),)
assert numero.formatar("29116000000042") == "2911.6-00.0000042"
assert len(numero.faixa("2911.6-00.0000042", "2911.6-00.0000044")) == 3
```

A validação aceita 14 ou 16 dígitos e confere mês e tipo, sem aplicar dígito
verificador. UF é mantida como texto de dois dígitos, sem associação com códigos
IBGE. O ano é o inteiro de dois dígitos, sem inferência de século. A faixa exige
extremos com o mesmo prefixo e comprimento, em ordem crescente.

Essas verificações não consultam emissão, titularidade ou situação no SNCR e
não comprovam validade legal. Veja as fontes e os formatos em
[DATA_SOURCES.md](https://github.com/Voa-Health/sncr/blob/main/DATA_SOURCES.md).

</details>

### Categorias FHIR R5

<details>
<summary>Ver uso e interpretação</summary>

```python
from sncr import fhir

categorias = fhir.categorias(["clonazepam"])
assert categorias[0]["coding"][0]["code"] == "B1"
assert categorias[0]["coding"][1]["code"] == "NRB"
```

`fhir.categorias` gera um elemento de `MedicationRequest.category` por lista,
deduplicado e na ordem da Portaria. Os codings incluem lista e receituário,
com códigos textuais e a atualização da norma em `version`.

O `text` é curto: identifica a lista, sinaliza adendos e, quando aplicável,
a ausência de receituário de controle associado. Os adendos integrais continuam
em `Classificacao.pendencias`. Princípios vazios são ignorados; entrada vazia
gera `[]`.

Sem correspondência em nenhum princípio informado, o resultado usa o código
`sem-lista`. Ele indica ausência de correspondência no catálogo, **não ausência
de controle nem autorização de prescrição**.

</details>

## Mais

- [Fontes de dados](https://github.com/Voa-Health/sncr/blob/main/DATA_SOURCES.md) ·
  [Relatório de extração](https://github.com/Voa-Health/sncr/blob/main/docs/extracao.md) ·
  [Changelog](https://github.com/Voa-Health/sncr/blob/main/CHANGELOG.md)
- [Contribuição](https://github.com/Voa-Health/sncr/blob/main/CONTRIBUTING.md) ·
  [Código de conduta](https://github.com/Voa-Health/sncr/blob/main/CODE_OF_CONDUCT.md) ·
  [Segurança](https://github.com/Voa-Health/sncr/blob/main/SECURITY.md)
- [Licença Apache-2.0](https://github.com/Voa-Health/sncr/blob/main/LICENSE)
