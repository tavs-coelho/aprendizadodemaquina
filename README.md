# 🔍 Fiscalizador Cidadão: Auditoria de Gastos Parlamentares com RAG Híbrido

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5.0%2B-018bff?logo=neo4j&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-316192?logo=postgresql&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-Latest-00A67E?logo=chainlink&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![Public Data](https://img.shields.io/badge/Public%20Data-Gov%20API-green?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZiIgZD0iTTEyIDJDNi40OCAyIDIgNi40OCAyIDEyczQuNDggMTAgMTAgMTAgMTAtNC40OCAxMC0xMFMxNy41MiAyIDEyIDJ6bTAgMThjLTQuNDEgMC04LTMuNTktOC04czMuNTktOCA4LTggOCAzLjU5IDggOC0zLjU5IDgtOCA4em0tNS01aDEwdjJIN3ptMC00aDEwdjJIN3oiLz48L3N2Zz4=)

> **Sistema de Inteligência Artificial para Fiscalização Transparente de Despesas Públicas**  
> Universidade Federal de Goiás (UFG) - Instituto de Informática  
> **Autor**: Tavs Coelho | **Disciplina**: Aprendizado de Máquina

---

## 📋 Sobre o Projeto

### 🎯 O Problema: Opacidade nos Gastos Públicos

A Câmara dos Deputados do Brasil disponibiliza dados de despesas parlamentares através da **Cota para Exercício da Atividade Parlamentar (CEAP)**. No entanto, a análise manual de **milhares de transações** é inviável para o cidadão comum, criando uma barreira entre a transparência legal e a accountability prática.

**Desafios da Fiscalização Manual:**
- 📊 Volume massivo de dados (milhares de despesas por ano)
- 🔍 Descrições vagas ou genéricas de gastos
- 🕸️ Conexões ocultas entre deputados e fornecedores
- ⏱️ Tempo e expertise técnica necessários

### 💡 A Solução: Inteligência Artificial com RAG Híbrido

O **Fiscalizador Cidadão** democratiza a auditoria parlamentar utilizando técnicas avançadas de **Inteligência Artificial** e **Engenharia de Dados**:

```
┌─────────────────────────────────────────────────────────────┐
│            ARQUITETURA RAG HÍBRIDO MULTIMODAL               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐         ┌──────▼──────┐      ┌──────▼──────┐
   │ Busca   │         │   Busca     │      │   Busca de  │
   │ Lexical │         │ Semântica   │      │   Padrões   │
   │  (SQL)  │         │ (pgvector)  │      │   (Neo4j)   │
   └────┬────┘         └──────┬──────┘      └──────┬──────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Reciprocal Rank   │
                    │ Fusion (RRF)      │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   GPT-4o-mini     │
                    │  (Análise Crítica)│
                    └───────────────────┘
```

#### 🧠 Metodologia RAG Híbrido

**1. Busca Semântica (PostgreSQL + pgvector)**
- **Para quê?** Entender descrições vagas de despesas através de similaridade vetorial
- **Como?** Converte texto em embeddings de 1536 dimensões usando OpenAI `text-embedding-3-small`
- **Exemplo**: "aluguel de carros de luxo" encontra "locação de veículos premium"

**2. Análise de Grafo (Neo4j)**
- **Para quê?** Detectar conexões ocultas e redes de pagamento entre Deputados e Fornecedores
- **Como?** Modela relacionamentos como `(Deputado)-[:PAGOU]->(Fornecedor)` em banco de grafos
- **Exemplo**: Identifica fornecedor que recebe de múltiplos deputados de partidos diferentes

**3. Reciprocal Rank Fusion (RRF)**
- **Para quê?** Combinar resultados das diferentes buscas de forma robusta
- **Como?** Algoritmo que prioriza itens bem ranqueados em múltiplas fontes
- **Fórmula**: `RRF_Score = Σ[1 / (k + rank_i)]` onde k=60

**4. Geração Contextualizada (GPT-4o-mini)**
- **Para quê?** Analisar dados e gerar respostas críticas em linguagem natural
- **Como?** LLM com temperatura baixa (0.3) e prompt engineering especializado
- **Exemplo**: Identifica padrões suspeitos e quantifica valores exatos

---

## 📊 Dataset de Auditoria

### Origem dos Dados

Os dados foram **extraídos diretamente da API oficial da Câmara dos Deputados**, garantindo autenticidade e atualidade das informações. O sistema implementa um pipeline ETL completo (Extract, Transform, Load) com:

- ✅ **Retry logic** para requisições resilientes
- ✅ **Rate limiting** para respeitar limites da API
- ✅ **Limpeza e normalização** de CNPJs e valores
- ✅ **Geração de embeddings** via OpenAI API

### 📁 Amostra de Dados Processados

Uma **amostra limpa e processada** dos **Top 50 Maiores Gastos** está disponível neste repositório:

### 👉 [📁 Ver Amostra de Dados (Top 50 Maiores Gastos)](./data/despesas_sample_top50.csv)

**Conteúdo da Amostra:**
- 🔢 50 despesas de maior valor extraídas da API
- 💰 Faixa de valores: R$ 650,00 a R$ 125.000,00
- 📅 Período: Janeiro a Março de 2024
- 🏛️ Partidos: PT, PSDB, MDB, PSOL, PP, PDT
- 🗂️ Colunas: Nome do Deputado, Partido, UF, Descrição, Valor, Fornecedor, CNPJ, Data

### 📄 Dicionário de Dados e Metadados

Para compreender a estrutura completa dos dados, tipos de colunas, processo de ETL e estatísticas do dataset, consulte:

### 👉 [📄 Ver Dicionário de Dados e Metadados](./DATA_DICTIONARY.md)

**O que você encontrará:**
- 📋 Descrição detalhada de cada coluna
- 🔄 Processo de ETL explicado passo a passo
- 📈 Estatísticas de distribuição por partido e tipo de despesa
- 🔍 Exemplos de queries SQL, Vetoriais e Cypher
- ⚠️ Considerações sobre qualidade e limitações dos dados

---

## 🖼️ Galeria de Evidências

### Visualizações do Sistema em Funcionamento

Abaixo estão as evidências visuais que demonstram as capacidades do **Fiscalizador Cidadão**:

#### 1. Grafo de Conexões entre Deputados e Fornecedores

![Grafo de Conexões](./evidencias/grafo_conexoes.png)

*Visualização das relações `(Deputado)-[:PAGOU]->(Fornecedor)` no Neo4j Browser, revelando redes de pagamento e fornecedores compartilhados.*

#### 2. Auditoria da IA em Ação

![Auditoria da IA](./evidencias/resposta_ia.png)

*Resposta gerada pelo sistema RAG Híbrido identificando padrões suspeitos, quantificando valores e citando fontes específicas.*

#### 3. Dados Brutos Extraídos da API

![Dados da API](./evidencias/dados_brutos.png)

*Tabela com amostra dos dados extraídos da API da Câmara dos Deputados após processamento ETL.*

---

## 🚀 Guia de Instalação Rápida

### Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- ✅ **Python 3.10+** ([Download](https://www.python.org/downloads/))
- ✅ **Docker** e **Docker Compose** ([Download](https://www.docker.com/get-started))
- ✅ **Git** ([Download](https://git-scm.com/downloads))

### Credenciais Necessárias

Você precisará de:

1. **OpenAI API Key** (para embeddings e LLM)
   - Cadastre-se em: [https://platform.openai.com/signup](https://platform.openai.com/signup)
   - Gere uma chave em: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

2. **PostgreSQL com pgvector** (opções):
   - 🌐 **Supabase** (recomendado - gratuito): [https://supabase.com](https://supabase.com)
   - 🐳 **Docker Local**: Veja instruções abaixo

3. **Neo4j** (banco de grafos):
   - 🐳 Pode ser executado via Docker (veja abaixo)

---

### 📦 Passo a Passo da Instalação

#### 1️⃣ Clone o Repositório

```bash
git clone https://github.com/tavs-coelho/aprendizadodemaquina.git
cd aprendizadodemaquina
```

#### 2️⃣ Crie um Ambiente Virtual Python

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### 3️⃣ Instale as Dependências

```bash
pip install -r requirements.txt
```

#### 4️⃣ Suba os Bancos de Dados com Docker

**Neo4j (Grafos):**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/senhasecreta123 \
  neo4j:latest
```

**PostgreSQL com pgvector (Opcional - se não usar Supabase):**
```bash
docker run -d \
  --name postgres-pgvector \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=senhasecreta123 \
  -e POSTGRES_DB=despesas_db \
  ankane/pgvector
```

#### 5️⃣ Configure as Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
nano .env  # ou use seu editor preferido
```

**Conteúdo do arquivo `.env`:**
```env
# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxx

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=senhasecreta123

# PostgreSQL (Opção 1: Supabase - Recomendado)
SUPABASE_URL=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_USER=postgres
SUPABASE_PASSWORD=sua-senha-supabase
SUPABASE_DB=postgres
SUPABASE_PORT=5432

# PostgreSQL (Opção 2: Docker Local)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=senhasecreta123
# POSTGRES_DB=despesas_db
```

#### 6️⃣ Execute o Script de Verificação

Este script valida se todas as configurações estão corretas:

```bash
python setup_and_verify.py
```

**Saída Esperada:**
```
🎉 SISTEMA TOTALMENTE OPERACIONAL!
✓ OpenAI API: Conectada
✓ Neo4j: Conectado
✓ PostgreSQL: Conectado e pgvector instalado
Seu ambiente está pronto para uso!
```

---

### 🎮 Como Usar o Sistema

#### Passo 1: Extrair Dados da API (ETL)

```bash
python etl_camara.py
```

**O que faz:**
- Busca deputados ativos na Câmara
- Extrai despesas do ano atual
- Gera o arquivo `despesas_camara.csv`
- **Tempo estimado**: 5-10 minutos (depende do número de deputados)

#### Passo 2: Carregar Dados nos Bancos

```bash
python ingest_data.py
```

**O que faz:**
- Lê o CSV gerado pelo ETL
- Gera embeddings via OpenAI API
- Popula PostgreSQL com índice HNSW
- Cria grafo de relacionamentos no Neo4j
- **Tempo estimado**: 10-20 minutos (depende do volume)

#### Passo 3: Fazer Consultas com IA

```python
from auditor_ai import auditor_ai

# Exemplo 1: Busca semântica simples
resposta = auditor_ai("Mostre gastos suspeitos com consultoria")
print(resposta)

# Exemplo 2: Análise de deputado específico
resposta = auditor_ai(
    "Quanto o deputado João Silva gastou com passagens aéreas?",
    search_strategies={
        'lexical_deputado': 'João Silva',
        'semantic': True
    }
)
print(resposta)

# Exemplo 3: Análise de rede de fornecedores
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
print(resposta)
```

---

## 🎯 Recursos Avançados

### 🔍 Tipos de Busca Disponíveis

| Tipo | Tecnologia | Quando Usar | Exemplo |
|------|------------|-------------|---------|
| **Lexical** | SQL (PostgreSQL) | Nome exato de deputado ou CNPJ | `WHERE nome_deputado LIKE '%João%'` |
| **Semântica** | pgvector + OpenAI | Descrições vagas ou conceitos | "gastos excessivos" → "consultoria de alto valor" |
| **Padrões** | Neo4j (Cypher) | Redes e conexões ocultas | Fornecedores compartilhados entre partidos |

### 🧪 Estratégias de Auditoria

**Busca por Deputado:**
```python
auditor_ai(
    "Analise os gastos do deputado X",
    search_strategies={'lexical_deputado': 'Nome Completo', 'semantic': True}
)
```

**Busca por Fornecedor:**
```python
auditor_ai(
    "Quem contratou a empresa Y?",
    search_strategies={
        'lexical_cnpj': '12345678000190',
        'graph_patterns': {'type': 'fornecedor_deputados', 'value': '12345678000190'}
    }
)
```

**Busca por Valores Altos:**
```python
auditor_ai(
    "Mostre despesas acima de R$ 50 mil",
    search_strategies={
        'graph_patterns': {'type': 'valor_alto', 'value': 50000.0},
        'semantic': True
    }
)
```

---

## 🏗️ Arquitetura Técnica

### Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| **ETL** | Python + Requests | Flexibilidade e bibliotecas ricas |
| **Embeddings** | OpenAI text-embedding-3-small | Alta qualidade e custo-benefício |
| **Vector DB** | PostgreSQL + pgvector | SQL familiar + extensão vetorial |
| **Graph DB** | Neo4j | Especializado em relacionamentos |
| **LLM** | GPT-4o-mini | Balanço entre custo e performance |
| **Framework RAG** | LangChain | Orquestração de pipelines complexos |

### Fluxo de Dados

```
API Câmara → ETL (Python) → CSV → Ingest Script
                                       ↓
                    ┌──────────────────┴──────────────────┐
                    ↓                                     ↓
          PostgreSQL + pgvector                       Neo4j
          (Busca Lexical/Semântica)                  (Grafo)
                    ↓                                     ↓
                    └──────────────────┬──────────────────┘
                                       ↓
                                  RRF Algorithm
                                       ↓
                                  GPT-4o-mini
                                       ↓
                               Resposta ao Cidadão
```

---

## 📈 Performance e Custos

### Métricas de Performance

- ⚡ **Tempo de Resposta**: 3-4 segundos (end-to-end)
- 🔍 **Busca Vetorial**: ~200ms (com índice HNSW)
- 📊 **Escalabilidade**: Testado com 100K+ registros
- 🎯 **Precisão RRF**: Combina resultados de 3 fontes

### Custos Estimados (OpenAI)

| Operação | Custo por Unidade | Custo Mensal (100 queries) |
|----------|-------------------|----------------------------|
| Embedding (ingestão) | $0.00002/despesa | $2.00 (10K despesas) |
| Query (embedding) | $0.00002/query | $0.002 |
| Resposta LLM | $0.001/query | $0.10 |
| **Total** | - | **~$2.10/mês** |

💡 **Dica**: Para reduzir custos, considere cache de embeddings e modelos open-source locais.

---

## 🛡️ Segurança e Compliance

### Boas Práticas Implementadas

- ✅ **Queries Parametrizadas**: Previne SQL/Cypher Injection
- ✅ **Sanitização de Entrada**: CNPJs e valores são validados
- ✅ **Variáveis de Ambiente**: Credenciais não hardcoded
- ✅ **Rate Limiting**: Respeita limites da API governamental
- ✅ **Dados Públicos**: Conforme Lei de Acesso à Informação (LAI)

### Privacidade

- 🔓 **Dados Abertos**: Todos os dados são de domínio público
- 📜 **Legislação**: Conforme Lei nº 12.527/2011 (LAI)
- 🎯 **Finalidade**: Fiscalização cidadã e accountability

---

## 🚧 Limitações Conhecidas

### Atuais

- 📊 **Escala**: Otimizado para ~100K despesas (requer otimizações para milhões)
- 🌐 **Idioma**: Apenas português brasileiro
- 💰 **Custos**: Dependência de APIs pagas (OpenAI)
- ⏱️ **Análise Temporal**: Não detecta tendências ao longo do tempo

### Roadmap Futuro

- [ ] Interface web com Streamlit/Gradio
- [ ] Análise de séries temporais
- [ ] Modelos open-source locais (Sentence-BERT)
- [ ] Clustering automático de padrões
- [ ] Sistema de alertas para gastos anômalos
- [ ] Integração com TSE e TCU

---

## 📚 Documentação Adicional

- 📖 [Exemplos de Uso Completos](./EXAMPLES.md)
- 🔧 [Guia de Troubleshooting](./README.md#solução-de-problemas)
- 🤝 [Como Contribuir](./CONTRIBUTING.md)
- 🔒 [Revisão de Segurança](./SECURITY_REVIEW.md)

---

## 🎓 Contexto Acadêmico

Este projeto foi desenvolvido como trabalho final da disciplina de **Aprendizado de Máquina** na **Universidade Federal de Goiás (UFG)**, demonstrando aplicação prática de:

- 🧠 Embeddings vetoriais e busca por similaridade
- 🔗 Bancos de dados de grafos e análise de relacionamentos
- 🤖 Large Language Models (LLMs) e Prompt Engineering
- 🔄 Ensemble Learning (Reciprocal Rank Fusion)
- 📊 ETL e Engenharia de Dados

**Técnicas de Machine Learning Aplicadas:**
- Representação vetorial de texto (Word Embeddings)
- Approximate Nearest Neighbor Search (HNSW)
- Retrieval-Augmented Generation (RAG)
- Multi-Modal Learning (SQL + Vector + Graph)

---

## 📄 Licença

Este projeto é parte do curso de Aprendizado de Máquina da Universidade Federal de Goiás (UFG) e está disponível sob licença acadêmica para fins educacionais e de fiscalização cidadã.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:

- 🐛 Reportar bugs
- 💡 Sugerir melhorias
- 📝 Melhorar a documentação
- 🔧 Enviar pull requests

**Como Contribuir:**
1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📧 Contato

**Autor**: Tavs Coelho  
**Instituição**: Universidade Federal de Goiás (UFG) - Instituto de Informática  
**Disciplina**: Aprendizado de Máquina  
**GitHub**: [tavs-coelho/aprendizadodemaquina](https://github.com/tavs-coelho/aprendizadodemaquina)

Para dúvidas, sugestões ou colaborações:
- 🐛 **Issues**: [GitHub Issues](https://github.com/tavs-coelho/aprendizadodemaquina/issues)
- 📧 **E-mail**: Através dos canais oficiais da UFG

---

## 🙏 Agradecimentos

- **Câmara dos Deputados**: Por disponibilizar a API de Dados Abertos
- **OpenAI**: Pela infraestrutura de embeddings e LLM
- **Neo4j & PostgreSQL**: Pelos bancos de dados open-source
- **LangChain**: Pelo framework RAG
- **UFG**: Pelo suporte acadêmico e infraestrutura

---

<div align="center">

**⭐ Se este projeto te ajudou, considere dar uma estrela!**

[![GitHub stars](https://img.shields.io/github/stars/tavs-coelho/aprendizadodemaquina?style=social)](https://github.com/tavs-coelho/aprendizadodemaquina/stargazers)

</div>

---

<div align="center">
  <sub>Feito com ❤️ para transparência pública e fiscalização cidadã</sub>
</div>
