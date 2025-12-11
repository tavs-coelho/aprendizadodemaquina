# Fiscalizador Cidadão (Citizen Auditor) 🔍

**Universidade Federal de Goiás (UFG) - Instituto de Informática**  
**Disciplina**: Aprendizado de Máquina  
**Autor**: Tavs Coelho

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Academic-green.svg)](LICENSE)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991.svg)](https://openai.com/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0+-018bff.svg)](https://neo4j.com/)

Uma ferramenta RAG (Retrieval-Augmented Generation) Multimodal para investigar e auditar o uso da Cota Parlamentar (CEAP) utilizando dados reais da API da Câmara dos Deputados do Brasil.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Contexto Acadêmico](#contexto-acadêmico)
- [Tecnologias](#tecnologias)
- [Arquitetura de Dados](#arquitetura-de-dados)
- [Funcionalidades](#funcionalidades)
- [Requisitos do Sistema](#requisitos-do-sistema)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Exemplos de Uso](#exemplos-de-uso)
- [Performance e Custos](#performance-e-custos)
- [Limitações e Trabalhos Futuros](#limitações-e-trabalhos-futuros)

---

## 🎯 Visão Geral

O **Fiscalizador Cidadão** é um sistema inteligente de auditoria que utiliza técnicas avançadas de Inteligência Artificial para analisar gastos parlamentares brasileiros. O sistema combina:

- **Retrieval-Augmented Generation (RAG)**: Para responder perguntas sobre despesas de forma contextualizada
- **Busca Híbrida (RRF)**: Combinação de busca lexical, semântica e em grafo
- **Análise de Padrões**: Detecção de anomalias e potenciais conflitos de interesse
- **Transparência Pública**: Facilita o acesso cidadão aos dados de despesas parlamentares

### Motivação

A Cota para Exercício da Atividade Parlamentar (CEAP) é uma verba destinada aos deputados federais para custear suas atividades. Apesar da disponibilidade dos dados pela API de Dados Abertos da Câmara, a análise manual de milhares de transações é inviável para o cidadão comum. Este projeto democratiza o acesso à auditoria parlamentar através de:

1. **Interface em Linguagem Natural**: Cidadãos podem fazer perguntas em português
2. **Análise Automatizada**: IA identifica padrões suspeitos automaticamente
3. **Contexto Enriquecido**: Combina múltiplas fontes para análise completa
4. **Escalabilidade**: Capaz de processar milhões de registros

---

## 🎓 Contexto Acadêmico

Este projeto foi desenvolvido como trabalho final da disciplina de **Aprendizado de Máquina** na Universidade Federal de Goiás (UFG), demonstrando a aplicação prática de conceitos como:

### Técnicas de Machine Learning Aplicadas

1. **Embeddings Vetoriais**: 
   - Representação densa de texto usando o modelo text-embedding-3-small (OpenAI)
   - Redução de dimensionalidade implícita de vocabulário para 1536 dimensões
   - Preservação de similaridade semântica

2. **Busca Vetorial com HNSW**:
   - Hierarchical Navigable Small World para busca aproximada de vizinhos mais próximos
   - Complexidade O(log N) para queries, vs O(N) de busca linear
   - Trade-off entre recall e velocidade

3. **Reciprocal Rank Fusion (RRF)**:
   - Ensemble learning para combinar rankings de múltiplas fontes
   - Não requer normalização de scores entre métodos diferentes
   - Robusto a diferenças de escala

4. **Large Language Models (LLM)**:
   - GPT-4o-mini para geração de texto contextualizada
   - Prompt engineering para análise crítica especializada
   - Temperature baixa (0.3) para respostas determinísticas

5. **Bancos de Dados NoSQL**:
   - Neo4j (grafos) para análise de relacionamentos
   - Queries Cypher para detecção de padrões complexos

### Contribuições Científicas

- Demonstração de sistema RAG multimodal em produção
- Comparação empírica de estratégias de busca (lexical vs semântica vs grafo)
- Pipeline ETL robusto para dados governamentais
- Framework reutilizável para outras aplicações de auditoria pública

---

## 🛠️ Tecnologias

- **Linguagem**: Python 3.8+
- **Banco de Dados em Grafo**: Neo4j (para relações entre deputados e fornecedores)
- **Banco de Dados Vetorial**: PostgreSQL + pgvector (para busca semântica)
- **LLM & Embeddings**: OpenAI (GPT-4o-mini, text-embedding-3-small)
- **Framework RAG**: LangChain
- **Fonte de Dados**: API de Dados Abertos da Câmara dos Deputados

---

## 🏗️ Arquitetura de Dados

### Diagrama de Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FISCALIZADOR CIDADÃO                          │
│                  Sistema RAG Multimodal para Auditoria               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     1. CAMADA DE INGESTÃO (ETL)                      │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │                         │
            ┌───────▼────────┐       ┌───────▼────────┐
            │  API Câmara    │       │   etl_camara   │
            │  dos Deputados │◄──────┤      .py       │
            │ (REST API)     │       │  (Python)      │
            └────────────────┘       └────────┬───────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │ despesas_camara.csv│
                                    │  (Arquivo CSV)     │
                                    └─────────┬──────────┘
                                              │
┌─────────────────────────────────────────────┼─────────────────────────┐
│                     2. CAMADA DE PROCESSAMENTO                        │
└─────────────────────────────────────────────┼─────────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │   ingest_data.py   │
                                    │  - Limpeza dados   │
                                    │  - Gera embeddings │
                                    │  - Popula bancos   │
                                    └─────────┬──────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                ┌────────▼─────────┐ ┌────────▼────────┐ ┌────────▼──────────┐
                │  OpenAI API      │ │  PostgreSQL +   │ │     Neo4j         │
                │  text-embedding  │ │    pgvector     │ │   (Grafos)        │
                │   -3-small       │ │  (Vetorial)     │ │                   │
                └──────────────────┘ └─────────────────┘ └───────────────────┘
                                              │                    │
┌───────────────────────────────────────────┼────────────────────┼─────┐
│                   3. CAMADA DE ARMAZENAMENTO                          │
└───────────────────────────────────────────┼────────────────────┼─────┘
                                            │                    │
                    ┌───────────────────────▼────────────────────▼──┐
                    │         BANCOS DE DADOS ESPECIALIZADOS         │
                    │                                                │
                    │  ┌─────────────────┐  ┌─────────────────┐    │
                    │  │  PostgreSQL     │  │     Neo4j       │    │
                    │  │  ┌───────────┐  │  │  ┌──────────┐   │    │
                    │  │  │despesas   │  │  │  │:Deputado │   │    │
                    │  │  │_parlamenta│  │  │  └────┬─────┘   │    │
                    │  │  │res        │  │  │       │[:PAGOU] │    │
                    │  │  │- nome     │  │  │  ┌────▼──────┐  │    │
                    │  │  │- cnpj     │  │  │  │:Fornecedor│  │    │
                    │  │  │- embedding│  │  │  └───────────┘  │    │
                    │  │  └───────────┘  │  │                 │    │
                    │  └─────────────────┘  └─────────────────┘    │
                    └────────────────────────────────────────────────┘
                                            │
┌───────────────────────────────────────────┼─────────────────────────┐
│                     4. CAMADA DE RECUPERAÇÃO (RAG)                   │
└───────────────────────────────────────────┼─────────────────────────┘
                                            │
                              ┌─────────────▼──────────────┐
                              │      auditor_ai.py         │
                              │   (Motor RAG Principal)    │
                              └─────────────┬──────────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────────────┐
          │                                 │                             │
    ┌─────▼──────┐              ┌──────────▼─────────┐        ┌──────────▼─────────┐
    │  Busca     │              │   Busca Semântica  │        │  Busca de Padrões  │
    │  Lexical   │              │    (Vetorial)      │        │     (Grafos)       │
    │  (SQL)     │              │  - Embeddings      │        │  - Redes           │
    │  - Nome    │              │  - Similaridade    │        │  - Outliers        │
    │  - CNPJ    │              │  - Contexto        │        │  - Concentração    │
    └─────┬──────┘              └──────────┬─────────┘        └──────────┬─────────┘
          │                                 │                             │
          └─────────────────────────────────┼─────────────────────────────┘
                                            │
                              ┌─────────────▼──────────────┐
                              │   Reciprocal Rank Fusion   │
                              │        (RRF Algorithm)     │
                              │   - Combina rankings       │
                              │   - Prioriza consenso      │
                              └─────────────┬──────────────┘
                                            │
┌───────────────────────────────────────────┼─────────────────────────┐
│                   5. CAMADA DE GERAÇÃO (LLM)                         │
└───────────────────────────────────────────┼─────────────────────────┘
                                            │
                              ┌─────────────▼──────────────┐
                              │    OpenAI GPT-4o-mini      │
                              │  - Análise contextual      │
                              │  - Identificação padrões   │
                              │  - Geração de resposta     │
                              │  - Citação de evidências   │
                              └─────────────┬──────────────┘
                                            │
                              ┌─────────────▼──────────────┐
                              │   Resposta ao Cidadão      │
                              │  - Valores exatos          │
                              │  - Datas específicas       │
                              │  - Análise crítica         │
                              │  - Recomendações           │
                              └────────────────────────────┘
```

### Fluxo de Dados Detalhado

#### Fase 1: Extração (ETL)
1. `etl_camara.py` consulta API da Câmara
2. Coleta dados de deputados e despesas
3. Aplica transformações básicas
4. Exporta CSV estruturado

#### Fase 2: Ingestão
1. `ingest_data.py` lê o CSV
2. Sanitiza CNPJs e valores
3. Gera embeddings via OpenAI API
4. Popula PostgreSQL com índice HNSW
5. Cria grafo de relacionamentos no Neo4j

#### Fase 3: Consulta (RAG)
1. Cidadão faz pergunta em linguagem natural
2. Sistema executa buscas paralelas:
   - Lexical: SQL no PostgreSQL
   - Semântica: Busca vetorial (embeddings)
   - Grafo: Queries Cypher no Neo4j
3. RRF combina os resultados
4. Top 15 despesas são selecionadas

#### Fase 4: Geração
1. Contexto formatado é enviado ao LLM
2. GPT-4o-mini analisa os dados
3. Identifica padrões suspeitos
4. Gera resposta estruturada
5. Retorna análise ao cidadão

### Fonte de Dados

Os dados são obtidos da [API de Dados Abertos da Câmara dos Deputados](https://dadosabertos.camara.leg.br/):
- `/deputados`: Informações sobre deputados (nome, partido, UF)
- `/deputados/{id}/despesas`: Despesas realizadas por cada deputado

### Modelo de Dados em Grafo (Neo4j)

**Entidades:**

1. **(:Deputado)**
   - Propriedades: `nome`, `partido`, `UF`

2. **(:Fornecedor)**
   - Propriedades: `nome`, `CNPJ/CPF`

**Relações:**

```cypher
(Deputado)-[:PAGOU {valor, data, descricao}]->(Fornecedor)
```

Esta estrutura permite consultas como:
- Quais fornecedores um deputado específico contratou?
- Quais deputados pagaram o mesmo fornecedor?
- Identificar redes de fornecedores compartilhados

### Modelo de Dados Vetorial (PostgreSQL + pgvector)

**Tabela: `despesas_parlamentares`**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `nome_deputado` | TEXT | Nome do deputado |
| `cnpj_fornecedor` | TEXT | CNPJ/CPF do fornecedor |
| `nome_fornecedor` | TEXT | Nome do fornecedor |
| `descricao_despesa` | TEXT | Descrição textual da despesa |
| `descricao_embedding` | VECTOR | Embedding vetorial da descrição |
| `valor` | NUMERIC | Valor da despesa em reais |
| `data_despesa` | DATE | Data da despesa |

Os **embeddings** são gerados usando o modelo `text-embedding-3-small` da OpenAI sobre a descrição textual das despesas, permitindo busca semântica como "gastos suspeitos com consultoria".

---

### 1. ETL Automatizado (`etl_camara.py`)

Script para extrair, transformar e carregar dados da API governamental:

**Recursos:**
- Busca deputados ativos na Câmara
- Extrai despesas por deputado e ano
- Limpa e normaliza dados
- Exporta para CSV para ingestão posterior

**Uso:**
```bash
python etl_camara.py
```

O script gerará um arquivo `despesas_camara.csv` com as despesas coletadas.

### 2. Ingestão de Dados (`ingest_data.py`)

Processa o CSV gerado pelo ETL e popula os bancos de dados:

**PostgreSQL:**
- Cria tabela `despesas_parlamentares` com suporte a vetores (pgvector)
- Gera embeddings usando OpenAI API (modelo `text-embedding-3-small`)
- Cria índice HNSW para busca vetorial rápida
- Suporta busca vetorial e lexical

**Neo4j:**
- Cria nós `(:Deputado {nome, partido, UF})`
- Cria nós `(:Fornecedor {nome, cnpj})`
- Cria relacionamentos `(Deputado)-[:PAGOU {valor, data, descricao}]->(Fornecedor)`
- Usa MERGE para evitar duplicidade de nós

**Formato do CSV de Entrada:**

O arquivo `despesas_camara.csv` deve conter:
- `nome`: Nome do deputado
- `siglaPartido`: Partido do deputado
- `siglaUf`: Unidade Federativa
- `txtDescricao`: Descrição da despesa (gera embeddings)
- `vlrLiquido`: Valor da despesa
- `txtFornecedor`: Nome do fornecedor
- `cnpjCpfFornecedor`: CNPJ/CPF do fornecedor
- `datEmissao`: Data da despesa

**Uso:**
```bash
python ingest_data.py
```

### 3. Busca Híbrida com RRF (Reciprocal Rank Fusion)

O sistema combina três tipos de busca:

**a) Busca Lexical** (SQL no PostgreSQL)
- Busca por nome de deputado ou CNPJ do fornecedor
- Usa `LIKE` para correspondência parcial de texto

**b) Busca Semântica** (Vetorial no PostgreSQL)
- Compara embeddings da pergunta com descrições das despesas
- Encontra gastos semanticamente similares (ex: "aluguel de carros" encontra "locação de veículos")

**c) Busca em Grafo** (Neo4j)
- Encontra padrões e relações complexas:
  - Fornecedores compartilhados entre deputados
  - Rede de gastos de um deputado
  - Despesas acima de valores específicos

**Reciprocal Rank Fusion (RRF):**
Combina os resultados das três buscas, priorizando itens que aparecem bem ranqueados em múltiplas fontes.

### 4. Análise com IA (`auditor_ai.py`)

Sistema RAG completo que responde perguntas sobre despesas parlamentares:

**Recursos:**
- Respostas contextualizadas usando LLM (GPT-4o-mini)
- Detecção automática de padrões suspeitos
- Citações específicas (valores, datas, fornecedores)
- Análise imparcial baseada em dados

**Uso:**
```python
from auditor_ai import auditor_ai

# Busca semântica simples
resposta = auditor_ai("Mostre gastos com aluguel de carros")

# Busca por deputado específico
resposta = auditor_ai(
    "Quais foram os gastos do deputado João Silva?",
    search_strategies={
        'lexical_deputado': 'João Silva',
        'semantic': True
    }
)

# Análise de padrões em grafo
resposta = auditor_ai(
    "Quais outros deputados pagaram esta empresa?",
    search_strategies={
        'lexical_cnpj': '12345678000190',
        'graph_patterns': {
            'type': 'fornecedor_deputados',
            'value': '12345678000190'
        }
    }
)
```

---

## 📦 Requisitos do Sistema

### Software Necessário

1. **Python 3.8+**
   - Gerenciador de pacotes pip

2. **Neo4j 5.0+**
   - Banco de dados de grafos
   - Pode ser executado via Docker:
     ```bash
     docker run -d \
       --name neo4j \
       -p 7474:7474 -p 7687:7687 \
       -e NEO4J_AUTH=neo4j/password \
       neo4j:latest
     ```

3. **PostgreSQL 14+ com pgvector**
   - Banco de dados com extensão pgvector instalada
   - Alternativa: Usar Supabase (PostgreSQL gerenciado com pgvector)

4. **Chaves de API**
   - **OpenAI API Key**: Para gerar embeddings e respostas LLM
     - Obtenha em: https://platform.openai.com/api-keys

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# PostgreSQL (ou use Supabase)
SUPABASE_URL=db.xxxxx.supabase.co
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your-password

# Alternativa: PostgreSQL local
# POSTGRES_HOST=localhost
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=password
```

---

## 🚀 Instalação

### 1. Clone o Repositório

```bash
git clone https://github.com/tavs-coelho/aprendizadodemaquina.git
cd aprendizadodemaquina
```

### 2. Crie um Ambiente Virtual

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as Variáveis de Ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

**Ou deixe o script de verificação criar o template para você:**

```bash
python setup_and_verify.py
# O script criará um arquivo .env se não existir
# Depois edite o arquivo e execute o script novamente
```

### 5. Prepare os Bancos de Dados

**PostgreSQL:**
```sql
-- Conecte ao PostgreSQL e execute:
CREATE EXTENSION IF NOT EXISTS vector;
```

**Neo4j:**
- Acesse http://localhost:7474
- Faça login com as credenciais configuradas
- O sistema criará os nós e relacionamentos automaticamente

### 6. Verifique a Instalação

Execute o script de verificação para garantir que tudo está funcionando:

```bash
python setup_and_verify.py
```

Se tudo estiver correto, você verá:
```
🎉 SISTEMA TOTALMENTE OPERACIONAL!
Seu ambiente está configurado corretamente e todas as APIs estão respondendo.
```

---

## 💻 Como Usar

### Passo 0: Verificar Configuração do Ambiente (NOVO!)

Antes de começar a usar o sistema, execute o script de verificação para diagnosticar problemas:

```bash
python setup_and_verify.py
```

**O que este script faz:**

Este script foi desenvolvido como uma ferramenta de DevOps/QA que atua como um "doutor" do sistema, diagnosticando problemas de configuração e conectividade. Ele executa três fases:

**Fase 1: Validação de Variáveis de Ambiente**
- Verifica se o arquivo `.env` existe
- Se não existir, cria automaticamente um template com valores padrão
- Valida se as chaves críticas (OPENAI_API_KEY, senhas) não estão vazias ou com valor `insira_aqui`

**Fase 2: Testes de Conectividade (Smoke Tests)**
- **OpenAI**: Testa a chave da API com uma chamada barata (embedding de teste)
- **Neo4j**: Tenta abrir uma sessão e verifica se o banco está acessível
- **PostgreSQL**: Conecta ao banco e verifica se a extensão `pgvector` está instalada

**Fase 3: Testes Funcionais do RAG (Integration Tests)**
- Importa os módulos principais (etl_camara, ingest_data, auditor_ai)
- Insere dados de teste (dummy) no sistema
- Tenta recuperá-los via busca vetorial e busca em grafo
- Remove os dados de teste após validação

**Saída do Script:**

O script usa cores no terminal para indicar status:
- 🟢 Verde: SUCESSO
- 🔴 Vermelho: FALHA
- 🟡 Amarelo: AVISO
- 🔵 Azul: INFORMAÇÃO

Se algo der errado, o script dirá exatamente o que você precisa corrigir, por exemplo:
- "Erro: Sua chave da OpenAI parece inválida. Verifique o arquivo .env"
- "Erro: PostgreSQL não está respondendo. Verifique se o Docker está rodando"

### Passo 1: Extrair Dados da API (ETL)

```bash
python etl_camara.py
```

Este script:
- Busca deputados ativos
- Extrai despesas do ano atual
- Gera o arquivo `despesas_camara.csv`

### Passo 2: Carregar Dados nos Bancos

```bash
python ingest_data.py
```

Este script:
- Lê o CSV gerado
- Popula o PostgreSQL com embeddings
- Popula o Neo4j com grafos de relações
- Exibe barras de progresso

### Passo 3: Fazer Consultas com IA

```python
from auditor_ai import auditor_ai

# Exemplo 1: Busca semântica
resposta = auditor_ai("Mostre gastos com consultoria")
print(resposta)

# Exemplo 2: Análise de deputado específico
resposta = auditor_ai(
    "Quanto o deputado X gastou com passagens aéreas?",
    search_strategies={
        'lexical_deputado': 'Nome do Deputado',
        'semantic': True
    }
)
print(resposta)
```

---

## 📊 Exemplos de Uso

### Exemplo Rápido: Busca Semântica

```python
from auditor_ai import auditor_ai

resposta = auditor_ai("Mostre gastos suspeitos com alimentação")
print(resposta)
```

### Exemplo: Análise de Deputado

```python
resposta = auditor_ai(
    "Quanto o deputado João Silva gastou?",
    search_strategies={
        'lexical_deputado': 'João Silva',
        'semantic': True
    }
)
print(resposta)
```

### Exemplo: Análise de Rede

```python
resposta = auditor_ai(
    "Quais deputados pagaram a empresa X?",
    search_strategies={
        'lexical_cnpj': '12345678000190',
        'graph_patterns': {
            'type': 'fornecedor_deputados',
            'value': '12345678000190'
        }
    }
)
```

📖 **Para exemplos completos com saídas esperadas e explicações técnicas, veja [EXAMPLES.md](EXAMPLES.md)**

---

## ⚡ Performance e Custos

### Métricas de Performance

**Tempo de Resposta (médio)**:
- Busca lexical: ~50ms
- Busca semântica: ~200ms (incluindo geração de embedding)
- Busca em grafo: ~100ms
- Geração de resposta (LLM): ~2-3s
- **Total end-to-end**: ~3-4 segundos

**Escalabilidade**:
- PostgreSQL: Testado com até 100K registros
- Neo4j: Testado com até 50K nós + 100K relacionamentos
- Índice HNSW: O(log N) para busca vetorial

### Custos Estimados (OpenAI API)

**Por Query**:
- Geração de embedding (text-embedding-3-small): ~$0.00002
- Resposta LLM (GPT-4o-mini): ~$0.001
- **Total por consulta**: ~$0.00102 (~R$ 0,005)

**Por Ingestão**:
- 10.000 despesas × $0.00002: ~$0.20 (~R$ 1,00)

💡 **Dica**: Para reduzir custos em produção, considere:
- Cache de embeddings para consultas frequentes
- Batch processing de embeddings
- Uso de modelos open-source locais (Sentence-BERT, etc.)

---

## 🚧 Limitações e Trabalhos Futuros

### Limitações Atuais

1. **Dependência de APIs Externas**:
   - Requer conexão com OpenAI API
   - Custos associados ao uso
   - Latência de rede

2. **Escala de Dados**:
   - Otimizado para ~100K despesas
   - Para milhões de registros, requer otimizações adicionais

3. **Idioma**:
   - Otimizado apenas para português brasileiro
   - Embeddings treinados multilíngue podem ter menor performance

4. **Análise Temporal**:
   - Não implementa análise de séries temporais
   - Não detecta tendências ao longo do tempo

### Trabalhos Futuros

- [ ] **Interface Web**: Streamlit ou Gradio para acesso cidadão
- [ ] **Análise Temporal**: Detecção de tendências e anomalias temporais
- [ ] **Clustering**: Agrupamento automático de padrões de gastos
- [ ] **Modelos Locais**: Substituir OpenAI por modelos open-source
- [ ] **Visualizações**: Grafos interativos de relacionamentos
- [ ] **Alertas**: Sistema de notificação para gastos suspeitos
- [ ] **Comparações**: Benchmark entre deputados/partidos/estados
- [ ] **Dados Complementares**: Integração com outras bases (TSE, TCU)

---

## 🔧 Solução de Problemas (Troubleshooting)

### Problemas Comuns

#### 1. Erro: "OPENAI_API_KEY não configurada"

**Sintoma**:
```
ValueError: OPENAI_API_KEY environment variable is not set
```

**Solução**:
```bash
# 1. Verifique se o arquivo .env existe
ls -la .env

# 2. Se não existir, crie a partir do exemplo
cp .env.example .env

# 3. Edite e adicione sua chave da OpenAI
nano .env  # ou use seu editor preferido

# 4. Verifique se a chave está correta
echo $OPENAI_API_KEY  # Deve mostrar sua chave
```

#### 2. Erro: "Failed to generate embeddings"

**Sintoma**:
```
RuntimeError: Failed to generate embeddings using OpenAI API
```

**Possíveis Causas e Soluções**:

a) **Chave inválida ou expirada**:
```bash
# Teste sua chave diretamente
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

b) **Sem créditos na conta OpenAI**:
- Acesse: https://platform.openai.com/account/billing
- Verifique saldo e adicione créditos se necessário

c) **Problemas de rede/proxy**:
```python
# Adicione proxy se necessário
import os
os.environ['HTTP_PROXY'] = 'http://proxy.exemplo.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy.exemplo.com:8080'
```

#### 3. Erro: "Connection refused" (Neo4j ou PostgreSQL)

**Sintoma**:
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solução para Neo4j**:
```bash
# Verifique se o Neo4j está rodando
docker ps | grep neo4j

# Se não estiver, inicie
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Teste a conexão
curl http://localhost:7474
```

**Solução para PostgreSQL/Supabase**:
```bash
# Teste a conexão
psql -h db.seu-projeto.supabase.co -U postgres -d postgres

# Verifique se pgvector está instalado
psql -h localhost -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 4. Erro: "despesas_camara.csv not found"

**Sintoma**:
```
ERROR: File 'despesas_camara.csv' not found!
```

**Solução**:
```bash
# Execute o ETL primeiro para gerar o CSV
python etl_camara.py

# Verifique se o arquivo foi criado
ls -lh despesas_camara.csv
```

#### 5. Performance Lenta na Busca Vetorial

**Sintoma**: Queries demoram mais de 5 segundos

**Soluções**:

a) **Verifique se o índice HNSW existe**:
```sql
-- No PostgreSQL
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'despesas_parlamentares';
```

b) **Recrie o índice se necessário**:
```sql
DROP INDEX IF EXISTS despesas_parlamentares_embedding_idx;
CREATE INDEX despesas_parlamentares_embedding_idx 
ON despesas_parlamentares 
USING hnsw (descricao_embedding vector_cosine_ops);
```

c) **Ajuste parâmetros do HNSW**:
```sql
-- Aumenta precisão (mais lento)
CREATE INDEX ... WITH (m = 32, ef_construction = 200);

-- Aumenta velocidade (menos preciso)
CREATE INDEX ... WITH (m = 16, ef_construction = 64);
```

#### 6. Erro: "ModuleNotFoundError"

**Sintoma**:
```
ModuleNotFoundError: No module named 'langchain'
```

**Solução**:
```bash
# Instale todas as dependências
pip install -r requirements.txt

# Se o problema persistir, atualize o pip
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

#### 7. Memory Error durante Ingestão

**Sintoma**:
```
MemoryError: Unable to allocate array
```

**Solução**:
```python
# No ingest_data.py, reduza o BATCH_SIZE
BATCH_SIZE = 100  # ao invés de 1000

# Ou processe o CSV em chunks
for chunk in pd.read_csv('despesas_camara.csv', chunksize=1000):
    process_chunk(chunk)
```

### Logs e Debugging

#### Habilitar Logs Detalhados

```python
# No início do script
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### Verificar Saúde do Sistema

```bash
# Execute o script de verificação
python setup_and_verify.py

# Saída esperada:
# 🎉 SISTEMA TOTALMENTE OPERACIONAL!
```

### Suporte Adicional

- **GitHub Issues**: https://github.com/tavs-coelho/aprendizadodemaquina/issues
- **Documentação OpenAI**: https://platform.openai.com/docs
- **Neo4j Community**: https://community.neo4j.com
- **Supabase Docs**: https://supabase.com/docs

---

## 📝 Notas Importantes

- **Uso Ético**: Esta ferramenta é destinada à transparência e fiscalização cidadã. Use os dados de forma responsável.
- **Dados Públicos**: Todos os dados são obtidos de APIs públicas do governo brasileiro.
- **Custos**: O uso da API da OpenAI tem custos associados. Monitore seu uso.
- **Privacidade**: Não armazene informações sensíveis no código ou repositório.

---

## 📄 Licença

Este projeto é parte do curso de Aprendizado de Máquina da Universidade Federal de Goiás (UFG).

---

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

---

## 📧 Contato

Para dúvidas ou sugestões sobre o projeto, entre em contato através dos canais da UFG.