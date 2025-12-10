# Aprendizado de Máquina - UFG

Este será um projeto da Universidade Federal de Goiás (UFG).

## Como Usar

### Interface Interativa de Terminal

Para usar o sistema de recomendação de filmes com interface interativa:

```bash
python rag_pipeline.py
```

O sistema iniciará uma interface de linha de comando onde você pode:
1. Digitar perguntas sobre filmes
2. (Opcional) Fornecer um título de filme relacionado para melhorar as recomendações
3. Receber respostas geradas pela IA usando RAG (Retrieval-Augmented Generation)

Para sair do programa, digite `sair`, `exit` ou `quit`, ou pressione `Ctrl+C`.

#### Exemplo de Uso

```
RAG Pipeline - Sistema de Recomendação de Filmes
==================================================
Digite 'sair' ou 'exit' para encerrar o programa
==================================================

Digite sua pergunta sobre filmes:
> Me recomende filmes de ação

Digite um título de filme relacionado (ou deixe em branco para busca geral):
> Matrix

Processando sua pergunta...

==================================================
RESPOSTA:
==================================================
[Resposta da IA com recomendações de filmes]
==================================================
```

## Funcionalidades

### Ingestão de Dados de Despesas da Câmara

O script `ingest_data.py` processa dados de despesas da Câmara dos Deputados e os armazena em dois bancos de dados: Neo4j (para busca em grafo) e PostgreSQL (para busca vetorial e lexical).

#### Uso

```bash
# Configure as variáveis de ambiente no arquivo .env
cp .env.example .env
# Edite o arquivo .env com suas credenciais

# Execute o script
python ingest_data.py
```

#### Formato do CSV

O arquivo `despesas_camara.csv` deve conter as seguintes colunas:
- `deputado_nome`: Nome do deputado
- `deputado_partido`: Partido do deputado
- `fornecedor_nome`: Nome do fornecedor
- `fornecedor_cnpj`: CNPJ do fornecedor
- `valor`: Valor da despesa (numérico)
- `data`: Data da despesa (formato YYYY-MM-DD)
- `txtDescricao`: Descrição da despesa (usado para gerar embeddings)

Um arquivo de exemplo está disponível em `despesas_camara_exemplo.csv`.

#### Funcionalidades

**PostgreSQL:**
- Cria tabela `despesas` com colunas para texto e embeddings
- Gera embeddings usando OpenAI API (modelo text-embedding-3-small)
- Cria índice HNSW para busca vetorial rápida
- Suporta busca vetorial e lexical

**Neo4j:**
- Cria nós `(:Deputado {nome, partido})`
- Cria nós `(:Fornecedor {nome, cnpj})`
- Cria relacionamentos `(Deputado)-[:PAGOU {valor, data, descricao}]->(Fornecedor)`
- Usa MERGE para evitar duplicidade de nós

#### Requisitos

Variáveis de ambiente necessárias (arquivo `.env`):
- `OPENAI_API_KEY`: Chave da API OpenAI
- `NEO4J_URI`: URI do banco Neo4j
- `NEO4J_USERNAME`: Usuário do Neo4j
- `NEO4J_PASSWORD`: Senha do Neo4j
- `POSTGRES_HOST` ou `SUPABASE_URL`: Host do PostgreSQL ou URL do Supabase
- `POSTGRES_USER` ou `SUPABASE_USER`: Usuário do PostgreSQL
- `POSTGRES_PASSWORD` ou `SUPABASE_PASSWORD`: Senha do PostgreSQL

#### Progresso

O script exibe barras de progresso usando `tqdm` para acompanhar:
- Inserção de dados no PostgreSQL (com geração de embeddings)
- Inserção de dados no Neo4j (nós e relacionamentos)

### Indexação de Documentos PDF

A função `index_documents` permite processar documentos PDF e armazená-los em um banco de dados vetorial local para busca por similaridade.

#### Uso

```python
from rag_pipeline import index_documents

# Processar um PDF e criar um banco de dados vetorial
vectorstore = index_documents("caminho/para/documento.pdf", chunk_size=1000)

# Realizar busca por similaridade
resultados = vectorstore.similarity_search("sua consulta aqui", k=5)
```

#### Parâmetros

- `pdf_path` (str, obrigatório): Caminho para o arquivo PDF a ser processado
- `chunk_size` (int, opcional): Tamanho dos chunks de texto. Padrão: 1000 caracteres

#### Retorno

Retorna um objeto FAISS vectorstore contendo os chunks do documento com seus embeddings.

#### Requisitos

- Variável de ambiente `OPENAI_API_KEY` deve estar configurada
- O arquivo PDF deve existir no caminho especificado

#### Dependências

As seguintes bibliotecas são utilizadas:
- `PyPDFLoader` (langchain-community): Para carregar documentos PDF
- `RecursiveCharacterTextSplitter` (langchain-text-splitters): Para dividir texto em chunks
- `FAISS` (faiss-cpu): Para armazenamento vetorial local
- `OpenAIEmbeddings` (langchain-openai): Para gerar embeddings dos textos