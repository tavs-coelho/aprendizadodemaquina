# 📄 Dicionário de Dados - Fiscalizador Cidadão

## Visão Geral

Este documento descreve a estrutura dos dados utilizados no projeto **Fiscalizador Cidadão**, incluindo metadados das colunas, tipos de dados, e informações sobre a origem e processamento.

---

## 📊 Fonte de Dados

**API de Dados Abertos da Câmara dos Deputados**

- **URL Base**: `https://dadosabertos.camara.leg.br/api/v2`
- **Endpoints Utilizados**:
  - `/deputados`: Lista de deputados federais ativos
  - `/deputados/{id}/despesas`: Despesas de um deputado específico por ano
- **Documentação Oficial**: [https://dadosabertos.camara.leg.br/swagger/api.html](https://dadosabertos.camara.leg.br/swagger/api.html)
- **Formato Original**: JSON (API REST)
- **Formato Processado**: CSV
- **Licença**: Dados públicos governamentais (Domínio Público)

---

## 📋 Estrutura do Dataset

### Arquivo: `despesas_sample_top50.csv`

Este arquivo contém uma **amostra dos 50 maiores gastos** extraídos da API, demonstrando despesas parlamentares de alto valor para facilitar análises e auditorias.

#### Colunas do Dataset

| # | Coluna | Tipo | Descrição | Exemplo | Observações |
|---|--------|------|-----------|---------|-------------|
| 1 | **nome_deputado** | `TEXT` | Nome completo do deputado federal | `João Silva` | Nome oficial registrado na Câmara |
| 2 | **siglaPartido** | `TEXT` | Sigla do partido político ao qual o deputado está filiado | `PT`, `PSDB`, `MDB` | Partido no momento da despesa |
| 3 | **siglaUf** | `TEXT` | Unidade Federativa (estado) que o deputado representa | `SP`, `RJ`, `MG` | Estados brasileiros (2 caracteres) |
| 4 | **txtDescricao** | `TEXT` | Descrição detalhada do tipo de despesa realizada | `Serviços de consultoria em tecnologia da informação` | Texto livre fornecido pela API |
| 5 | **vlrLiquido** | `NUMERIC` | Valor líquido da despesa em reais (R$) | `1500.00` | Valor após descontos e impostos |
| 6 | **txtFornecedor** | `TEXT` | Nome ou razão social do fornecedor que recebeu o pagamento | `Empresa ABC Ltda` | Pode ser pessoa física ou jurídica |
| 7 | **cnpjCpfFornecedor** | `TEXT` | CNPJ ou CPF do fornecedor (identificador fiscal) | `12.345.678/0001-90` | Formatado ou sem pontuação |
| 8 | **datEmissao** | `DATE` | Data de emissão do documento fiscal da despesa | `2024-01-15` | Formato: `YYYY-MM-DD` |

---

## 🔄 Processo de ETL (Extract, Transform, Load)

### 1. **Extração** (`etl_camara.py`)

- **Método**: Requisições HTTP GET à API REST da Câmara
- **Rate Limiting**: 0.5 segundos entre requisições para respeitar limites da API
- **Retry Logic**: Até 3 tentativas em caso de falha de rede
- **Timeout**: 10 segundos por requisição
- **Saída**: Arquivo `despesas_camara.csv`

### 2. **Transformação**

Durante o processamento, os seguintes transformações são aplicadas:

#### Limpeza de CNPJ/CPF
```python
# Remove pontuação e espaços
"12.345.678/0001-90" → "12345678000190"
```

#### Normalização de Valores Monetários
```python
# Converte strings para float
"R$ 1.500,00" → 1500.00
"1500,50" → 1500.50
```

#### Padronização de Datas
```python
# Formato ISO 8601
"15/01/2024" → "2024-01-15"
```

### 3. **Carregamento** (`ingest_data.py`)

Os dados são carregados em dois bancos de dados especializados:

#### a) PostgreSQL + pgvector
- **Tabela**: `despesas_parlamentares`
- **Colunas Adicionais**:
  - `descricao_embedding` (VECTOR): Embedding vetorial da descrição (1536 dimensões)
  - `id` (SERIAL): Chave primária auto-incrementada
- **Índice**: HNSW (Hierarchical Navigable Small World) para busca vetorial rápida
- **Modelo de Embedding**: OpenAI `text-embedding-3-small`

#### b) Neo4j (Banco de Grafos)
- **Nós**:
  - `(:Deputado {nome, partido, UF})`
  - `(:Fornecedor {nome, cnpj})`
- **Relações**:
  - `(Deputado)-[:PAGOU {valor, data, descricao}]->(Fornecedor)`

---

## 📈 Estatísticas do Dataset de Amostra

### Distribuição por Partido (Top 50)
- **PSDB**: 10 despesas
- **PT**: 10 despesas
- **MDB**: 10 despesas
- **PSOL**: 10 despesas
- **PP**: 5 despesas
- **PDT**: 5 despesas

### Distribuição por Valor
- **Maior Despesa**: R$ 125.000,00 (Consultoria Legal SA)
- **Menor Despesa**: R$ 650,00 (Sustenta Consultoria)
- **Valor Médio**: R$ 26.730,23
- **Valor Total**: R$ 1.336.510,85

### Distribuição por Tipo de Despesa (Top 5)
1. **Consultoria e Assessoria**: 18 despesas (36%)
2. **Locação (veículos, equipamentos, imóveis)**: 14 despesas (28%)
3. **Serviços de TI e Marketing**: 8 despesas (16%)
4. **Produção de Material**: 6 despesas (12%)
5. **Outros Serviços**: 4 despesas (8%)

---

## 🔍 Uso no Sistema RAG

### Busca Lexical (SQL)
```sql
SELECT * FROM despesas_parlamentares
WHERE nome_deputado LIKE '%João Silva%'
ORDER BY valor DESC;
```

### Busca Semântica (Vetorial)
```sql
SELECT *, 
  (descricao_embedding <=> '[embedding_da_query]') AS distance
FROM despesas_parlamentares
ORDER BY distance
LIMIT 10;
```

### Busca em Grafo (Cypher)
```cypher
MATCH (d:Deputado)-[r:PAGOU]->(f:Fornecedor)
WHERE r.valor >= 50000
RETURN d.nome, f.nome, r.valor
ORDER BY r.valor DESC;
```

---

## ⚠️ Considerações Importantes

### Qualidade dos Dados

1. **Completude**: Alguns registros podem ter campos vazios ou nulos (especialmente `cnpjCpfFornecedor`)
2. **Consistência**: Nomes de fornecedores podem variar ligeiramente (ex: "Empresa ABC Ltda" vs "Empresa ABC LTDA")
3. **Temporalidade**: Os dados refletem o ano fiscal consultado (padrão: ano atual)
4. **Duplicatas**: O sistema usa `MERGE` no Neo4j para evitar duplicação de nós

### Limitações

- **Amostra Reduzida**: O arquivo `despesas_sample_top50.csv` contém apenas 50 registros para demonstração
- **Dataset Completo**: Para análises completas, execute `etl_camara.py` para extrair todos os dados
- **Periodicidade**: A API da Câmara é atualizada continuamente; recomenda-se executar o ETL periodicamente

### Privacidade e Transparência

- ✅ **Dados Públicos**: Todos os dados são de domínio público por lei (Lei de Acesso à Informação)
- ✅ **Transparência**: Os nomes de deputados e fornecedores são informações públicas
- ✅ **Uso Ético**: O sistema é destinado à fiscalização cidadã e accountability governamental

---

## 📚 Referências

- **Lei de Acesso à Informação (LAI)**: Lei nº 12.527/2011
- **API Dados Abertos**: [https://dadosabertos.camara.leg.br](https://dadosabertos.camara.leg.br)
- **Resolução da Câmara sobre CEAP**: Ato da Mesa nº 43/2009

---

## 🔄 Versionamento

- **Versão**: 1.0
- **Última Atualização**: Dezembro 2024
- **Autor**: Tavs Coelho - UFG
- **Disciplina**: Aprendizado de Máquina

---

## 📧 Contato para Dúvidas sobre os Dados

Para questões relacionadas à qualidade, estrutura ou interpretação dos dados, consulte:
- **GitHub Issues**: [https://github.com/tavs-coelho/aprendizadodemaquina/issues](https://github.com/tavs-coelho/aprendizadodemaquina/issues)
- **API Oficial**: [https://dadosabertos.camara.leg.br/howtouse/2019-03-13-dados-abertos.html](https://dadosabertos.camara.leg.br/howtouse/2019-03-13-dados-abertos.html)
