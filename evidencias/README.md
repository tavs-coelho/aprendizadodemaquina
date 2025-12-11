# 🖼️ Galeria de Evidências

Esta pasta contém as evidências visuais do sistema **Fiscalizador Cidadão** em funcionamento.

## 📸 Como Gerar as Evidências

Para gerar automaticamente as screenshots do sistema, execute:

```bash
python generate_evidence.py
```

Este script automatizado irá:
1. Capturar o grafo de relacionamentos do Neo4j
2. Gerar uma resposta da IA e capturar a tela
3. Exibir uma tabela com os dados brutos

## 🎯 Evidências Disponíveis

### 1. Grafo de Conexões
**Arquivo**: `grafo_conexoes.png`  
**Conteúdo**: Visualização das relações `(Deputado)-[:PAGOU]->(Fornecedor)` no Neo4j Browser

### 2. Auditoria da IA
**Arquivo**: `resposta_ia.png`  
**Conteúdo**: Resposta gerada pelo sistema RAG Híbrido identificando padrões suspeitos

### 3. Dados Brutos
**Arquivo**: `dados_brutos.png`  
**Conteúdo**: Tabela com amostra dos dados extraídos da API da Câmara

## ⚠️ Nota

Se as imagens não foram geradas ainda, você verá placeholders no README principal.  
Execute `generate_evidence.py` para criar as evidências reais.

## 🔧 Pré-requisitos

- Neo4j rodando em `http://localhost:7474`
- Playwright instalado (`pip install playwright && playwright install chromium`)
- Arquivo `.env` configurado com as credenciais
