# Fontes de dados

## Escopo

Listas da Portaria SVS/MS nº 344/1998 e normas complementares da Anvisa.
O catálogo associa tipos às siglas das listas; não inclui substâncias.

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

```sh
uv run python scripts/manutencao.py fontes
uv run python scripts/manutencao.py artefatos
uv run python scripts/manutencao.py artefatos --check
```

Os comandos de fontes e artefatos não alteram arquivos; não há geração automatizada de listas.
A classificação não substitui a leitura da norma.
