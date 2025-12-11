# Fiscalizador Cidadão (Citizen Auditor)

**Universidade Federal de Goiás (UFG)**

Uma ferramenta RAG Multimodal para investigar e auditar o uso da Cota Parlamentar (CEAP) utilizando dados reais da API da Câmara dos Deputados do Brasil.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Tecnologias](#tecnologias)
- [Arquitetura de Dados](#arquitetura-de-dados)
- [Funcionalidades](#funcionalidades)
- [Requisitos do Sistema](#requisitos-do-sistema)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Exemplos de Uso](#exemplos-de-uso)

---

## 🎯 Visão Geral

O **Fiscalizador Cidadão** é um sistema inteligente de auditoria que utiliza técnicas avançadas de Inteligência Artificial para analisar gastos parlamentares. O sistema combina:

- **Retrieval-Augmented Generation (RAG)**: Para responder perguntas sobre despesas de forma contextualizada
- **Busca Híbrida (RRF)**: Combinação de busca lexical, semântica e em grafo
- **Análise de Padrões**: Detecção de anomalias e potenciais conflitos de interesse

## 🛠️ Tecnologias

- **Linguagem**: Python 3.8+
- **Banco de Dados em Grafo**: Neo4j (para relações entre deputados e fornecedores)
- **Banco de Dados Vetorial**: PostgreSQL + pgvector (para busca semântica)
- **LLM & Embeddings**: OpenAI (GPT-4o-mini, text-embedding-3-small)
- **Framework RAG**: LangChain
- **Fonte de Dados**: API de Dados Abertos da Câmara dos Deputados

---

## 🏗️ Arquitetura de Dados

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

### Exemplo 1: Busca Semântica

```python
from auditor_ai import auditor_ai

resposta = auditor_ai("Mostre gastos suspeitos com alimentação")
print(resposta)
```

**Saída:**
```
Com base nos dados recuperados, identifiquei as seguintes despesas com alimentação:

1. Deputado: João Silva
   - Fornecedor: Restaurante XYZ
   - Valor: R$ 15.000,00
   - Data: 2024-03-15
   - Observação: Valor elevado para fornecimento de alimentação

2. Deputado: Maria Santos
   - Fornecedor: Catering ABC
   - Valor: R$ 8.500,00
   - Data: 2024-02-20
   ...
```

### Exemplo 2: Análise de Rede de Fornecedores

```python
resposta = auditor_ai(
    "Quais deputados fizeram pagamentos para a empresa com CNPJ 12345678000190?",
    search_strategies={
        'lexical_cnpj': '12345678000190',
        'graph_patterns': {
            'type': 'fornecedor_deputados',
            'value': '12345678000190'
        },
        'semantic': True
    }
)
print(resposta)
```

### Exemplo 3: Detecção de Anomalias

```python
resposta = auditor_ai(
    "Mostre despesas acima de R$ 50.000,00",
    search_strategies={
        'graph_patterns': {
            'type': 'valor_alto',
            'value': 50000
        },
        'semantic': True
    }
)
print(resposta)
```

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