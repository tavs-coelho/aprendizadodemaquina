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