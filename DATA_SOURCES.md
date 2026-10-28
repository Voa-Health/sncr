# Fontes de dados

## Escopo

Listas da Portaria SVS/MS nº 344/1998 e normas complementares da Anvisa.
O catálogo associa tipos às siglas das listas e inclui as designações nominais
do Anexo I, com sinônimos e adendos para revisão humana.

## Registro das fontes

Consulta em 2026-10-28. Os hashes correspondem aos PDFs consultados.

| Documento | URL oficial | Versão | SHA-256 |
| --- | --- | --- | --- |
| Manual da API SNCR | [PDF](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr/documentos-do-sncr/sncr_manual_api_v5.pdf/@@display-file/file) | 3ª edição, setembro/2026 | `dbaed56de26b42c739c5eedda5b688bf4c42249f75d151c5e57d6541e62a39bb` |
| Webinar SNCR 2.0 | [PDF](https://www.gov.br/anvisa/pt-br/assuntos/educacaoepesquisa/webinar/medicamentos/arquivos/sncr-webinar-1-sncr-2-0.pdf/@@display-file/file) | SNCR 2.0 | `3badc3f8be3d6dc2c179c374b64f1624ab68e669dc800b792d0de8d4dec95ed2` |
| Manual SNCR Farmácias | [PDF](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr/farmacias/manual_sncr_farmacias_1ed_2026_formatado_vf_publicacao.pdf/@@display-file/file) | 2ª edição, outubro/2026 | `2bc1ad0d02e2b85866c3c880db95204cf8b4ff5e529a7716565e612cd4cfa63e` |
| RDC 1.036/2026 | [AnvisaLegis, Anexo I](https://anvisalegis.datalegis.net/action/UrlPublicasAction.php?acao=abrirAtoPublico&num_ato=00001036&sgl_tipo=RDC&sgl_orgao=RDC/DC/ANVISA/MS&vlr_ano=2026&seq_ato=000&cod_modulo=134&cod_menu=1696) | 9 de julho de 2026 | — |
| Portaria SVS/MS 344/1998 | [AnvisaLegis](https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&tipo=POR&numeroAto=00000344&seqAto=000&valorAno=1998&orgao=SVS/MS&cod_menu=1696&cod_modulo=134&pesquisa=true) | Texto consolidado consultado | — |

## Correspondência

- Webinar: códigos 1–7, formato de 14 dígitos e RET sob a RDC 471/2021.
- Manual da API: notificações com 10–50 números por requisição e 50 por tipo,
  prescritor e dia; RCE/RET com 1.000 por requisição, três requisições mensais por
  inscrição profissional e 3.000 números mensais por tipo e profissional.
- Manual Farmácias: 16 dígitos com sequencial de nove; números de 14 dígitos
  emitidos anteriormente permanecem válidos.
- RDC 1.036/2026, cabeçalhos do Anexo I: associações entre listas e receituários.
  RET não atende a lista da Portaria 344; sua base é a RDC 471/2021.
- Portaria 344, art. 40: NRA amarela; art. 45: NRB azul.
  Não foi localizada cor explícita para NRB2 nesse texto; o catálogo usa `None`.

O campo UF permanece uma string de dois dígitos: o webinar não o identifica
como código IBGE. Não há dígito verificador documentado nas fontes consultadas.

## Reprodução

### Endpoints de integração

O Manual da API v5, seção de URL base, documenta:

- Produção: `https://api-gateway.prd.apps.anvisa.gov.br/api-sncr`.
- Homologação: `https://api-gateway.hmg.apps.anvisa.gov.br/api-sncr`.

O [webinar de integração de junho/2026](https://www.gov.br/anvisa/pt-br/assuntos/educacaoepesquisa/webinar/medicamentos/arquivos/sncr-webinar-integracao-plataforma-prescricoes-anvisa-junho-2026.pdf/@@display-file/file) também cita
`https://sncr-api.hmg.apps.anvisa.gov.br` como endereço de homologação.
SHA-256 do PDF: `0ea8b2b5c3e22c3a6c9a22f3b0aaf133e2ef46f2495dfb9aa36111fd70456002`.
Os dois endereços de homologação servem a especificação em `/v3/api-docs`.
O contrato consultado declara API **1.2.1** (`info.version`), no formato
OpenAPI **3.0.1**.
O cliente usa os gateways do Manual, sem fallback automático; os paths
de numeração são `/api/v1/numeracoes/notificacao-receita` e
`/api/v1/numeracoes/receita-especial-retencao`.

O contrato OpenAPI consultado descreve tanto erros 400 com `codigo/mensagem`
quanto `errorObject` e exemplos em lista. O cliente extrai mensagens
defensivamente, sem deduzir causas por seu texto.
O exemplo de faixa de controle especial da especificação apresenta quantidade
incompatível com os extremos inclusivos: o cliente exige consistência entre
`quantidade` e `len(faixa)`, em vez de aceitar essa divergência.

### Anexo I versionado

- Ato: **RDC nº 1.036, de 09/07/2026**.
- Número extraído do Anexo: **ATUALIZAÇÃO N. 101**.
- [Texto oficial ISO-8859-1](https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&tipo=RDC&numeroAto=00001036&seqAto=000&valorAno=2026&orgao=RDC/DC/ANVISA/MS&codTipo=&desItem=&desItemFim=&cod_menu=1696&cod_modulo=134&pesquisa=true).
- [Índice oficial de atualizações](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/lista-substancias).
- Arquivo bruto: `scripts/fontes/rdc1036.html`, obtido em **2026-10-28**.
- SHA-256: `bf6b1124d23cc9511673938fad3d6025af0d746318d014fefacbde5f42d903da`.
- Metadados: `scripts/fontes/rdc1036.json`.

O texto do ato oficial não tem proteção de direito autoral, conforme a
Lei 9.610/98, art. 8º, IV. Essa condição não estende a licença do pacote
a outros conteúdos ou elementos da página.

Os itens são extraídos por bloco HTML, preservando textos inline e a ordem.
Sinônimos vêm de um parêntese final balanceado no nome principal ou de
alternativas após `ou`. Estas são separadas por `;`, preservando parênteses
químicos; somente um `)` final desbalanceado da última alternativa é removido.
O [relatório de extração](docs/extracao.md) lista todas as aplicações dessas regras.
O número 55 se repete na lista F1 da fonte; ele não foi renumerado.
Em F2 há 186 substâncias nominais. As classes estruturais seguintes são preservadas
como pendências, não como nomes pesquisáveis; não se inferem correspondências químicas.

```sh
uv run python scripts/manutencao.py fontes
uv run python scripts/manutencao.py artefatos
uv run python scripts/manutencao.py artefatos --check
```

O comando `fontes` baixa a página e atualiza o bruto e seus metadados.
`artefatos` lê somente esses arquivos locais, verifica o hash e gera
`src/sncr/data/listas.json` e `docs/extracao.md` deterministicamente.
`artefatos --check` não escreve arquivos e falha se qualquer resultado divergir.
O JSON é incluído no wheel; a consulta não usa rede.
A classificação não substitui a leitura da norma; adendos exigem revisão humana.

### Cobertura CMED

`uv run python scripts/manutencao.py cobertura` lê a planilha oficial PF/PMC
com SUBSTÂNCIA, APRESENTAÇÃO e TARJA, sem instalar dependências adicionais.
A URL padrão é
`https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/precos/arquivos/lista_pmc__20261009_115232672.xlsx/@@download/file`,
publicada na [página de preços](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/precos).
Use `--arquivo caminho.xlsx` (ou CSV com esses cabeçalhos, separado por `;`)
para reprodução offline e `--url URL` para registrar outra origem.
O relatório informa URL e SHA-256; o arquivo não é persistido pelo comando.
Com arquivo local, a URL é uma declaração de origem, não uma verificação de autenticidade.

A unidade é uma linha de apresentação, sem deduplicação por EAN ou GGREM.
Uma apresentação casa se **algum** princípio casar; princípios de compostos são
separados por `;` na célula SUBSTÂNCIA. A coluna EXATO exclui correspondências
por derivado; COM DERIVADO inclui ambas. As tarjas são preservadas literalmente,
inclusive valores ausentes e marcadores da fonte. Cobertura não valida a tarja
nem determina o receituário de uma apresentação ou suas exceções de uso.
