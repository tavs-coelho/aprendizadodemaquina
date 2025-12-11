"""
Auditor AI - Sistema de RAG para Auditoria de Despesas Parlamentares
======================================================================

Este módulo implementa um sistema completo de Retrieval-Augmented Generation (RAG) 
para auditoria inteligente de despesas parlamentares brasileiras.

Arquitetura Multimodal:
-----------------------
O sistema combina três estratégias de busca para fornecer análises abrangentes:

1. **Busca Lexical (SQL no PostgreSQL)**
   - Busca exata por nome de deputado ou CNPJ de fornecedor
   - Utiliza índices tradicionais de banco de dados
   - Ideal para consultas específicas e filtros diretos

2. **Busca Semântica (Vetorial no PostgreSQL + pgvector)**
   - Busca por similaridade usando embeddings OpenAI (text-embedding-3-small)
   - Encontra gastos semanticamente relacionados mesmo com termos diferentes
   - Exemplo: "aluguel de carros" encontra "locação de veículos"

3. **Busca de Padrões (Grafos no Neo4j)**
   - Análise de relações entre deputados e fornecedores
   - Identificação de redes de pagamento
   - Detecção de padrões suspeitos e concentração de gastos

Fusão de Resultados:
-------------------
Os resultados das três buscas são combinados usando o algoritmo Reciprocal Rank 
Fusion (RRF), que prioriza itens que aparecem bem ranqueados em múltiplas fontes.

Geração de Resposta:
-------------------
Um Large Language Model (GPT-4o-mini) analisa os dados recuperados e gera 
respostas contextualizadas, identificando padrões suspeitos e fornecendo 
análises críticas baseadas em evidências.

Autor: Tavs Coelho - Universidade Federal de Goiás (UFG)
Curso: Aprendizado de Máquina
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional, Union
from urllib.parse import quote_plus
import pandas as pd
from neo4j import GraphDatabase
import openai
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Carregar variáveis de ambiente
load_dotenv()


def search_lexical(query: str, search_type: str = "deputado", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Realiza busca lexical (SQL) no PostgreSQL por deputado ou fornecedor.
    
    Esta função implementa busca tradicional de banco de dados usando índices SQL.
    É otimizada para consultas exatas ou parciais usando LIKE pattern matching.
    
    Casos de Uso:
    ------------
    - Buscar despesas de um deputado específico pelo nome
    - Buscar todas as transações com um fornecedor específico pelo CNPJ
    - Filtrar despesas por critérios exatos
    
    Args:
        query (str): Termo de busca (nome do deputado ou CNPJ do fornecedor)
        search_type (str): Tipo de busca - "deputado" ou "cnpj" (padrão: "deputado")
        limit (int): Número máximo de resultados retornados (padrão: 10)
    
    Returns:
        List[Dict[str, Any]]: Lista de dicionários contendo informações das despesas:
            - nome_deputado: Nome completo do deputado
            - cnpj_fornecedor: CNPJ/CPF do fornecedor (sanitizado)
            - nome_fornecedor: Nome ou razão social do fornecedor
            - descricao_despesa: Descrição detalhada da despesa
            - valor: Valor em reais (BRL)
            - data_despesa: Data de emissão do documento
    
    Raises:
        ValueError: Se variáveis de ambiente do PostgreSQL não estiverem configuradas
        ValueError: Se search_type não for "deputado" ou "cnpj"
    
    Exemplo:
        >>> despesas = search_lexical("João Silva", search_type="deputado", limit=5)
        >>> print(f"Encontradas {len(despesas)} despesas")
        >>> print(f"Primeira despesa: R$ {despesas[0]['valor']}")
    
    Nota de Segurança:
        Utiliza queries parametrizadas do SQLAlchemy para prevenir SQL injection.
        Todas as queries usam o padrão :parameter para binding seguro.
    """
    # Obter credenciais do Postgres
    db_url = os.getenv("SUPABASE_URL")
    db_user = os.getenv("SUPABASE_USER")
    db_password = os.getenv("SUPABASE_PASSWORD")
    
    if not all([db_url, db_user, db_password]):
        raise ValueError(
            "Missing required Postgres environment variables. "
            "Please set SUPABASE_URL, SUPABASE_USER, and SUPABASE_PASSWORD."
        )
    
    # Construir connection string do PostgreSQL com codificação segura
    encoded_user = quote_plus(db_user)
    encoded_password = quote_plus(db_password)
    connection_string = f"postgresql://{encoded_user}:{encoded_password}@{db_url}"
    
    # Criar engine do SQLAlchemy
    engine = create_engine(connection_string)
    
    try:
        with engine.connect() as connection:
            if search_type == "deputado":
                # Busca por nome de deputado (case-insensitive, com LIKE)
                # SECURITY: Uses SQLAlchemy text() with parameterized query (:query, :limit)
                # to prevent SQL injection. All SQL queries in this file follow this pattern.
                sql_query = text("""
                    SELECT 
                        nome_deputado,
                        cnpj_fornecedor,
                        nome_fornecedor,
                        descricao_despesa,
                        valor,
                        data_despesa
                    FROM despesas_parlamentares
                    WHERE LOWER(nome_deputado) LIKE LOWER(:query)
                    ORDER BY data_despesa DESC
                    LIMIT :limit
                """)
                result = connection.execute(
                    sql_query, 
                    {"query": f"%{query}%", "limit": limit}
                )
            elif search_type == "cnpj":
                # Busca por CNPJ do fornecedor
                # SECURITY: Uses SQLAlchemy text() with parameterized query (:query, :limit)
                sql_query = text("""
                    SELECT 
                        nome_deputado,
                        cnpj_fornecedor,
                        nome_fornecedor,
                        descricao_despesa,
                        valor,
                        data_despesa
                    FROM despesas_parlamentares
                    WHERE cnpj_fornecedor = :query
                    ORDER BY data_despesa DESC
                    LIMIT :limit
                """)
                result = connection.execute(
                    sql_query, 
                    {"query": query, "limit": limit}
                )
            else:
                raise ValueError(f"Invalid search_type: {search_type}. Must be 'deputado' or 'cnpj'")
            
            # Converter resultados para lista de dicionários
            rows = result.fetchall()
            columns = result.keys()
            
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
    
    finally:
        engine.dispose()


def search_semantic(query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Realiza busca semântica usando embeddings vetoriais no PostgreSQL.
    
    Esta função converte a pergunta do usuário em um vetor usando o modelo
    text-embedding-3-small da OpenAI e busca despesas semanticamente similares
    no banco de dados usando a extensão pgvector.
    
    Vantagens da Busca Semântica:
    -----------------------------
    - Encontra conteúdo relacionado mesmo com vocabulário diferente
    - Compreende sinônimos e variações linguísticas
    - Captura o significado contextual da consulta
    - Não requer correspondência exata de palavras-chave
    
    Exemplos de Busca:
    -----------------
    - "aluguel de carros de luxo" → encontra "locação de veículos premium"
    - "gastos com alimentação" → encontra "despesas com refeições", "buffet", etc.
    - "consultoria suspeita" → encontra "serviços de assessoria" com valores altos
    
    Args:
        query_text (str): Pergunta ou descrição em linguagem natural
        limit (int): Número máximo de resultados (padrão: 10)
    
    Returns:
        List[Dict[str, Any]]: Lista de despesas ordenadas por similaridade, contendo:
            - nome_deputado: Nome do deputado
            - cnpj_fornecedor: CNPJ do fornecedor
            - nome_fornecedor: Nome do fornecedor
            - descricao_despesa: Descrição da despesa
            - valor: Valor em reais
            - data_despesa: Data da transação
            - distance: Distância vetorial (menor = mais similar)
    
    Raises:
        ValueError: Se OPENAI_API_KEY não estiver configurada
        ValueError: Se variáveis de ambiente do PostgreSQL não estiverem configuradas
        RuntimeError: Se falhar ao gerar embeddings via API da OpenAI
    
    Exemplo:
        >>> resultados = search_semantic("gastos excessivos com viagens", limit=5)
        >>> for r in resultados[:3]:
        ...     print(f"{r['nome_deputado']}: R$ {r['valor']:.2f}")
    
    Implementação Técnica:
        - Modelo de embedding: text-embedding-3-small (1536 dimensões)
        - Métrica de similaridade: Distância de cosseno (<=> operator)
        - Índice: HNSW (Hierarchical Navigable Small World) para performance
    """
    # Validar API key do OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY environment variable. "
            "Please set OPENAI_API_KEY to generate embeddings."
        )
    
    # Obter credenciais do Postgres
    db_url = os.getenv("SUPABASE_URL")
    db_user = os.getenv("SUPABASE_USER")
    db_password = os.getenv("SUPABASE_PASSWORD")
    
    if not all([db_url, db_user, db_password]):
        raise ValueError(
            "Missing required Postgres environment variables. "
            "Please set SUPABASE_URL, SUPABASE_USER, and SUPABASE_PASSWORD."
        )
    
    # Gerar embedding para a query usando OpenAI
    client = openai.OpenAI(api_key=openai_api_key)
    
    try:
        response = client.embeddings.create(
            input=query_text,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
    except Exception as e:
        raise RuntimeError(
            f"Failed to generate embeddings using OpenAI API. "
            f"Error: {e}"
        )
    
    # Construir connection string do PostgreSQL com codificação segura
    encoded_user = quote_plus(db_user)
    encoded_password = quote_plus(db_password)
    connection_string = f"postgresql://{encoded_user}:{encoded_password}@{db_url}"
    
    # Criar engine do SQLAlchemy
    engine = create_engine(connection_string)
    
    try:
        with engine.connect() as connection:
            # Busca vetorial usando operador de distância (assumindo extensão pgvector)
            # Usa operador <=> para distância de cosseno
            sql_query = text("""
                SELECT 
                    nome_deputado,
                    cnpj_fornecedor,
                    nome_fornecedor,
                    descricao_despesa,
                    valor,
                    data_despesa,
                    (descricao_embedding <=> CAST(:query_embedding AS vector)) AS distance
                FROM despesas_parlamentares
                WHERE descricao_embedding IS NOT NULL
                ORDER BY descricao_embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """)
            
            # Converter embedding para string formatada para PostgreSQL
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            result = connection.execute(
                sql_query,
                {"query_embedding": embedding_str, "limit": limit}
            )
            
            # Converter resultados para lista de dicionários
            rows = result.fetchall()
            columns = result.keys()
            
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
    
    finally:
        engine.dispose()


def search_graph_patterns(query_type: str, param_value: Union[str, float, int], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Consulta padrões complexos no grafo de relacionamentos do Neo4j.
    
    Esta função utiliza o poder dos bancos de dados de grafos para identificar
    padrões e relações entre deputados e fornecedores que seriam difíceis de
    detectar com queries SQL tradicionais.
    
    Tipos de Análise Disponíveis:
    -----------------------------
    
    1. **fornecedor_deputados**: Rede de deputados que pagaram um fornecedor
       - Identifica fornecedores que recebem de múltiplos deputados
       - Útil para detectar concentração de pagamentos
       - Retorna: deputados, número de transações, total pago
    
    2. **deputado_fornecedores**: Rede de fornecedores de um deputado
       - Mostra todos os fornecedores contratados por um deputado
       - Identifica preferências e padrões de contratação
       - Retorna: fornecedores, frequência, valor total
    
    3. **valor_alto**: Despesas acima de um threshold
       - Filtra transações de alto valor
       - Útil para auditoria de outliers
       - Retorna: deputado, fornecedor, valor, descrição
    
    Args:
        query_type (str): Tipo de análise - veja "Tipos de Análise" acima
        param_value (Union[str, float, int]): Parâmetro da busca:
            - Para "fornecedor_deputados": CNPJ do fornecedor
            - Para "deputado_fornecedores": Nome do deputado (parcial)
            - Para "valor_alto": Valor mínimo (float)
        limit (int): Número máximo de resultados (padrão: 10)
    
    Returns:
        List[Dict[str, Any]]: Lista de padrões encontrados. Estrutura varia por tipo:
            - fornecedor_deputados/deputado_fornecedores:
                {nome_deputado, nome_fornecedor, cnpj_fornecedor, 
                 num_transacoes, total_pago}
            - valor_alto:
                {nome_deputado, nome_fornecedor, cnpj_fornecedor,
                 descricao_despesa, valor, data_despesa}
    
    Raises:
        ValueError: Se variáveis de ambiente do Neo4j não estiverem configuradas
        ValueError: Se query_type for inválido
    
    Exemplos:
        >>> # Encontrar deputados que pagaram a empresa X
        >>> rede = search_graph_patterns(
        ...     "fornecedor_deputados", 
        ...     "12345678000190", 
        ...     limit=20
        ... )
        >>> print(f"{len(rede)} deputados pagaram este fornecedor")
        
        >>> # Gastos acima de R$ 50.000
        >>> altos = search_graph_patterns("valor_alto", 50000.0, limit=10)
        >>> for g in altos:
        ...     print(f"{g['nome_deputado']}: R$ {g['valor']:.2f}")
    
    Nota de Segurança:
        Utiliza queries parametrizadas do Neo4j ($param) para prevenir
        Cypher injection. O driver Neo4j sanitiza automaticamente os parâmetros.
    """
    # Obter credenciais do Neo4j
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        raise ValueError(
            "Missing required Neo4j environment variables. "
            "Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )
    
    # Criar driver do Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            if query_type == "fornecedor_deputados":
                # Encontrar outros deputados que pagaram o mesmo fornecedor
                query = """
                MATCH (f:Fornecedor {cnpj: $param_value})<-[:PAGOU]-(d:Deputado)
                OPTIONAL MATCH (d)-[r:PAGOU]->(f)
                WITH d, f, COUNT(r) AS num_transacoes, SUM(r.valor) AS total_pago
                RETURN 
                    d.nome AS nome_deputado,
                    f.nome AS nome_fornecedor,
                    f.cnpj AS cnpj_fornecedor,
                    num_transacoes,
                    total_pago
                ORDER BY total_pago DESC
                LIMIT $limit
                """
                result = session.run(query, param_value=param_value, limit=limit)
                
            elif query_type == "deputado_fornecedores":
                # Encontrar fornecedores pagos por um deputado específico
                query = """
                MATCH (d:Deputado)-[r:PAGOU]->(f:Fornecedor)
                WHERE LOWER(d.nome) CONTAINS LOWER($param_value)
                WITH d, f, COUNT(r) AS num_transacoes, SUM(r.valor) AS total_pago
                RETURN 
                    d.nome AS nome_deputado,
                    f.nome AS nome_fornecedor,
                    f.cnpj AS cnpj_fornecedor,
                    num_transacoes,
                    total_pago
                ORDER BY total_pago DESC
                LIMIT $limit
                """
                result = session.run(query, param_value=param_value, limit=limit)
                
            elif query_type == "valor_alto":
                # Encontrar deputados com despesas acima de um valor
                query = """
                MATCH (d:Deputado)-[r:PAGOU]->(f:Fornecedor)
                WHERE r.valor >= $param_value
                RETURN 
                    d.nome AS nome_deputado,
                    f.nome AS nome_fornecedor,
                    f.cnpj AS cnpj_fornecedor,
                    r.descricao AS descricao_despesa,
                    r.valor AS valor,
                    r.data AS data_despesa
                ORDER BY r.valor DESC
                LIMIT $limit
                """
                result = session.run(query, param_value=float(param_value), limit=limit)
                
            else:
                raise ValueError(
                    f"Invalid query_type: {query_type}. "
                    f"Must be 'fornecedor_deputados', 'deputado_fornecedores', or 'valor_alto'"
                )
            
            # Converter resultados para lista de dicionários
            results = []
            for record in result:
                results.append(dict(record))
            
            return results
    
    finally:
        driver.close()


def reciprocal_rank_fusion(search_results: List[List[str]], k: int = 60) -> pd.DataFrame:
    """
    Aplica o algoritmo Reciprocal Rank Fusion (RRF) para combinar múltiplos rankings.
    
    O RRF é uma técnica de fusão de rankings que combina resultados de diferentes
    métodos de busca de forma robusta e eficiente. A grande vantagem é que o RRF
    não requer normalização de scores entre diferentes métodos de busca.
    
    Algoritmo:
    ---------
    Para cada item que aparece em qualquer ranking, calculamos:
    
        RRF_Score(item) = Σ [ 1 / (k + rank_i) ]
        
    Onde:
    - rank_i: posição do item no i-ésimo ranking (1-indexed)
    - k: constante que controla o peso do ranking (padrão: 60)
    - Σ: soma sobre todos os rankings onde o item aparece
    
    Propriedades:
    ------------
    - Items que aparecem em múltiplos rankings recebem score mais alto
    - Items bem ranqueados (posição 1, 2, 3) têm maior contribuição
    - Listas vazias são automaticamente ignoradas
    - Robusto a diferenças de tamanho entre listas
    
    Args:
        search_results (List[List[str]]): Lista de rankings, onde cada ranking
            é uma lista de IDs ordenados por relevância (primeiro = mais relevante)
        k (int): Constante de suavização RRF (padrão: 60, valor recomendado na literatura)
    
    Returns:
        pd.DataFrame: DataFrame com colunas 'despesa_id' e 'rrf_score',
            ordenado por rrf_score em ordem decrescente (maior score = mais relevante)
    
    Exemplo:
        >>> # Três buscas diferentes retornam resultados parcialmente sobrepostos
        >>> lexical_results = ['id1', 'id2', 'id3']
        >>> semantic_results = ['id1', 'id4', 'id5']
        >>> graph_results = ['id2', 'id1', 'id6']
        >>> 
        >>> fused = reciprocal_rank_fusion(
        ...     [lexical_results, semantic_results, graph_results],
        ...     k=60
        ... )
        >>> print(fused.head())
        #   despesa_id  rrf_score
        # 0       id1   0.049180  <- Aparece em todas as 3 listas
        # 1       id2   0.032895  <- Aparece em 2 listas
        
    Referência:
        Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
        Reciprocal rank fusion outperforms condorcet and individual rank 
        learning methods. SIGIR '09.
    """
    # Dicionário para acumular scores RRF para cada despesa
    rrf_scores = {}
    
    # Iterar através de cada lista de resultados de busca
    for search_result in search_results:
        # Iterar através de cada item na lista com seu rank (1-indexed)
        for rank, item_id in enumerate(search_result, start=1):
            # Calcular a contribuição para o score RRF
            score_contribution = 1 / (k + rank)
            
            # Adicionar a contribuição ao score total da despesa
            rrf_scores[item_id] = rrf_scores.get(item_id, 0) + score_contribution
    
    # Converter o dicionário para DataFrame
    df = pd.DataFrame(list(rrf_scores.items()), columns=['despesa_id', 'rrf_score'])
    
    # Ordenar por rrf_score em ordem decrescente
    df = df.sort_values(by='rrf_score', ascending=False).reset_index(drop=True)
    
    return df


def format_expense_context(expenses: List[Dict[str, Any]]) -> str:
    """
    Formata lista de despesas em texto estruturado para o LLM.
    
    Esta função converte dados estruturados de despesas em um formato textual
    legível que será usado como contexto para o Large Language Model (LLM).
    A formatação é otimizada para facilitar a análise do modelo.
    
    Args:
        expenses (List[Dict[str, Any]]): Lista de dicionários de despesas, onde cada
            dicionário pode conter:
            - nome_deputado: Nome do deputado
            - nome_fornecedor: Nome do fornecedor
            - cnpj_fornecedor: CNPJ/CPF do fornecedor
            - descricao_despesa: Descrição da despesa
            - valor: Valor monetário
            - data_despesa: Data da transação
            - num_transacoes: (opcional) Número de transações agregadas
            - total_pago: (opcional) Total pago em múltiplas transações
    
    Returns:
        str: Texto formatado com todas as despesas, uma por parágrafo.
             Se a lista estiver vazia, retorna "Nenhuma despesa encontrada."
    
    Exemplo de Saída:
        ```
        Despesa 1:
        - Deputado: João Silva
        - Fornecedor: Empresa ABC Ltda
        - CNPJ: 12345678000190
        - Descrição: Locação de veículos
        - Valor: R$ 15000.00
        - Data: 2024-03-15
        
        Despesa 2:
        - Deputado: Maria Santos
        - Fornecedor: Consultoria XYZ
        - CNPJ: 98765432000110
        - Descrição: Serviços de consultoria
        - Valor: R$ 45000.00
        - Data: 2024-02-20
        ```
    """
    if not expenses:
        return "Nenhuma despesa encontrada."
    
    context_parts = []
    
    for i, expense in enumerate(expenses, 1):
        expense_text = f"Despesa {i}:\n"
        expense_text += f"- Deputado: {expense.get('nome_deputado', 'N/A')}\n"
        expense_text += f"- Fornecedor: {expense.get('nome_fornecedor', 'N/A')}\n"
        expense_text += f"- CNPJ: {expense.get('cnpj_fornecedor', 'N/A')}\n"
        expense_text += f"- Descrição: {expense.get('descricao_despesa', 'N/A')}\n"
        expense_text += f"- Valor: R$ {expense.get('valor', 0):.2f}\n"
        expense_text += f"- Data: {expense.get('data_despesa', 'N/A')}\n"
        
        # Adicionar informações extras se disponíveis (de buscas de padrões)
        if 'num_transacoes' in expense:
            expense_text += f"- Número de Transações: {expense.get('num_transacoes')}\n"
        if 'total_pago' in expense:
            expense_text += f"- Total Pago: R$ {expense.get('total_pago', 0):.2f}\n"
        
        context_parts.append(expense_text)
    
    return "\n".join(context_parts)


def _create_expense_id(expense):
    """
    Cria um ID único para uma despesa baseado em seus campos principais.
    
    Usa hash SHA256 para garantir IDs consistentes e determinísticos.
    
    Args:
        expense: Dicionário contendo informações da despesa
    
    Returns:
        str: ID único para a despesa
    """
    # Criar ID baseado em campos-chave para identificação única
    id_parts = [
        str(expense.get('nome_deputado', '')),
        str(expense.get('cnpj_fornecedor', '')),
        str(expense.get('valor', '')),
        str(expense.get('data_despesa', ''))
    ]
    # Usar hashlib.sha256 para criar um ID determinístico
    id_string = '|'.join(id_parts)
    return hashlib.sha256(id_string.encode('utf-8')).hexdigest()[:16]


def auditor_ai(user_question: str, search_strategies: Optional[Dict[str, Any]] = None) -> str:
    """
    Sistema RAG completo para auditoria inteligente de despesas parlamentares.
    
    Esta é a função principal do sistema Fiscalizador Cidadão. Ela orquestra
    todo o pipeline RAG: busca multimodal, fusão de rankings e geração de
    resposta com análise crítica usando IA.
    
    Fluxo de Execução:
    -----------------
    1. **Coleta de Dados**: Executa buscas paralelas em múltiplas fontes
       - Busca lexical (SQL)
       - Busca semântica (vetorial)
       - Busca de padrões (grafos)
    
    2. **Fusão de Rankings**: Aplica RRF para combinar resultados
       - Prioriza itens que aparecem em múltiplas buscas
       - Cria ranking consolidado
    
    3. **Geração de Contexto**: Formata os dados para o LLM
    
    4. **Análise com IA**: LLM (GPT-4o-mini) analisa os dados e gera resposta
       - Identifica padrões suspeitos
       - Quantifica valores e datas
       - Fornece análise crítica profissional
    
    Args:
        user_question (str): Pergunta do cidadão sobre despesas parlamentares
            Exemplos:
            - "Mostre gastos suspeitos com alimentação"
            - "Quanto o deputado João Silva gastou em 2024?"
            - "Quais deputados contrataram a empresa X?"
        
        search_strategies (Optional[Dict[str, Any]]): Dicionário configurando
            quais estratégias de busca usar. Se None, usa apenas busca semântica.
            
            Opções disponíveis:
            - 'lexical_deputado' (str): Nome do deputado para busca SQL
            - 'lexical_cnpj' (str): CNPJ para busca SQL
            - 'semantic' (bool): Se True, executa busca semântica
            - 'graph_patterns' (dict): Configuração para busca em grafo
                * 'type': tipo de análise (ver search_graph_patterns)
                * 'value': parâmetro da análise
    
    Returns:
        str: Resposta gerada pelo Auditor AI com análise detalhada das despesas,
             incluindo valores exatos, nomes, datas e observações críticas.
    
    Raises:
        ValueError: Se OPENAI_API_KEY não estiver configurada
    
    Exemplos de Uso:
    ---------------
    
    Exemplo 1: Busca semântica simples
        >>> resposta = auditor_ai("Mostre gastos com aluguel de carros")
        >>> print(resposta)
        Com base nos dados recuperados, identifiquei as seguintes despesas...
    
    Exemplo 2: Análise de deputado específico
        >>> resposta = auditor_ai(
        ...     "Quais foram os gastos do deputado João Silva?",
        ...     search_strategies={
        ...         'lexical_deputado': 'João Silva',
        ...         'semantic': True
        ...     }
        ... )
    
    Exemplo 3: Análise de rede de fornecedores
        >>> resposta = auditor_ai(
        ...     "Quais deputados pagaram a empresa X?",
        ...     search_strategies={
        ...         'lexical_cnpj': '12345678000190',
        ...         'graph_patterns': {
        ...             'type': 'fornecedor_deputados',
        ...             'value': '12345678000190'
        ...         }
        ...     }
        ... )
    
    Configuração do LLM:
    -------------------
    - Modelo: gpt-4o-mini (custo-benefício otimizado)
    - Temperature: 0.3 (baixa para respostas objetivas e consistentes)
    - System Prompt: Especializado em auditoria crítica
    
    Performance:
    -----------
    - Tempo médio: 2-5 segundos (depende de chamadas à API OpenAI)
    - Máximo de despesas analisadas: 15 (top do ranking RRF)
    - Geração de embeddings: ~0.1s por consulta
    """
    # Validar API key do OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY environment variable. "
            "Please set OPENAI_API_KEY to use the ChatOpenAI model."
        )
    
    # Coletar resultados de diferentes buscas para aplicar RRF
    search_result_lists = []
    all_expenses_dict = {}  # Para armazenar os detalhes das despesas
    
    # Se nenhuma estratégia foi especificada, usar apenas busca semântica
    if search_strategies is None:
        search_strategies = {'semantic': True}
    
    # Busca Lexical por Deputado
    if 'lexical_deputado' in search_strategies:
        deputado_name = search_strategies['lexical_deputado']
        try:
            lexical_results = search_lexical(deputado_name, search_type="deputado", limit=10)
            # Criar IDs únicos para cada despesa
            result_ids = []
            for expense in lexical_results:
                expense_id = _create_expense_id(expense)
                result_ids.append(expense_id)
                all_expenses_dict[expense_id] = expense
            search_result_lists.append(result_ids)
        except Exception as e:
            logger.warning(f"Lexical search by deputado failed: {e}")
    
    # Busca Lexical por CNPJ
    if 'lexical_cnpj' in search_strategies:
        cnpj = search_strategies['lexical_cnpj']
        try:
            cnpj_results = search_lexical(cnpj, search_type="cnpj", limit=10)
            result_ids = []
            for expense in cnpj_results:
                expense_id = _create_expense_id(expense)
                result_ids.append(expense_id)
                all_expenses_dict[expense_id] = expense
            search_result_lists.append(result_ids)
        except Exception as e:
            logger.warning(f"Lexical search by CNPJ failed: {e}")
    
    # Busca Semântica
    if search_strategies.get('semantic'):
        try:
            semantic_results = search_semantic(user_question, limit=10)
            result_ids = []
            for expense in semantic_results:
                expense_id = _create_expense_id(expense)
                result_ids.append(expense_id)
                all_expenses_dict[expense_id] = expense
            search_result_lists.append(result_ids)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
    
    # Busca de Padrões no Grafo
    if 'graph_patterns' in search_strategies:
        pattern_config = search_strategies['graph_patterns']
        try:
            pattern_results = search_graph_patterns(
                pattern_config.get('type'),
                pattern_config.get('value'),
                limit=10
            )
            result_ids = []
            for expense in pattern_results:
                expense_id = _create_expense_id(expense)
                result_ids.append(expense_id)
                all_expenses_dict[expense_id] = expense
            search_result_lists.append(result_ids)
        except Exception as e:
            logger.warning(f"Graph pattern search failed: {e}")
    
    # Aplicar Reciprocal Rank Fusion se houver múltiplos resultados
    if len(search_result_lists) > 1:
        # Usar RRF para combinar e rankear resultados
        fused_df = reciprocal_rank_fusion(search_result_lists, k=60)
        # Pegar os top resultados ranqueados
        top_expense_ids = fused_df['despesa_id'].head(15).tolist()
        # Recuperar as despesas correspondentes
        final_expenses = [all_expenses_dict[exp_id] for exp_id in top_expense_ids if exp_id in all_expenses_dict]
    elif len(search_result_lists) == 1:
        # Se só temos uma busca, usar os resultados diretos (sem duplicatas)
        unique_ids = list(dict.fromkeys(search_result_lists[0]))  # Preserva ordem
        final_expenses = [all_expenses_dict[exp_id] for exp_id in unique_ids[:15]]
    else:
        # Nenhuma busca retornou resultados
        final_expenses = []
    
    # Formatar contexto
    context = format_expense_context(final_expenses)
    
    # Se não encontrou nenhuma despesa
    if not final_expenses:
        return ("Desculpe, não encontrei despesas parlamentares relevantes para sua pergunta. "
                "Tente reformular sua pergunta ou verificar se os dados estão disponíveis no sistema.")
    
    # Criar System Prompt específico para Auditor Cidadão
    system_prompt = """Você é um Auditor Cidadão Imparcial especializado em análise de despesas públicas. 

Sua função é analisar despesas parlamentares de forma crítica e analítica, respondendo às perguntas dos cidadãos de maneira objetiva, clara e baseada em evidências.

SEMPRE cite informações específicas dos dados:
- Valores EXATOS das despesas (em R$)
- Nomes COMPLETOS dos deputados envolvidos
- Nomes e CNPJs das empresas/fornecedores
- Datas ESPECÍFICAS das transações
- Descrições DETALHADAS das despesas

Como um auditor profissional, você deve:
1. ANALISAR CRITICAMENTE os dados apresentados
2. IDENTIFICAR padrões suspeitos ou incomuns, incluindo:
   - Valores desproporcionalmente altos para serviços comuns ou genéricos
   - Concentração de pagamentos: múltiplas transações para o mesmo fornecedor
   - Descrições vagas ou genéricas combinadas com valores elevados
   - Padrões temporais suspeitos (ex: gastos concentrados em períodos específicos)
   - Fornecedores que recebem de múltiplos deputados
   - Valores atípicos ou outliers em relação à média
3. QUANTIFICAR sempre que possível (ex: "Total pago: R$ X", "Média de gastos: R$ Y")
4. CONTEXTUALIZAR os gastos quando relevante
5. Ser CÉTICO mas JUSTO - apontar tanto aspectos positivos quanto preocupantes

IMPORTANTE: Base suas observações EXCLUSIVAMENTE nos dados fornecidos. Se não houver dados suficientes para uma conclusão, mencione isso explicitamente.

Seja factual, objetivo e mantenha um tom profissional de análise forense financeira."""

    # Criar template de prompt
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template=f"""{system_prompt}

Contexto das Despesas Parlamentares:
{{context}}

Pergunta do Cidadão:
{{question}}

Resposta do Auditor:"""
    )
    
    # Inicializar ChatOpenAI com gpt-4o-mini
    llm = ChatOpenAI(
        model='gpt-4o-mini',
        temperature=0.3,  # Temperatura baixa para respostas mais objetivas
        openai_api_key=openai_api_key
    )
    
    # Criar chain usando LangChain Expression Language (LCEL)
    output_parser = StrOutputParser()
    chain = prompt_template | llm | output_parser
    
    # Gerar e retornar resposta final
    response = chain.invoke({
        "context": context,
        "question": user_question
    })
    
    return response


# Exemplo de uso
if __name__ == "__main__":
    load_dotenv()
    
    # Exemplo 1: Busca simples semântica
    print("=== Exemplo 1: Busca Semântica ===")
    try:
        resposta = auditor_ai(
            "Mostre gastos com aluguel de carros de luxo"
        )
        print(resposta)
    except Exception as e:
        print(f"Erro: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Exemplo 2: Busca por deputado específico
    print("=== Exemplo 2: Busca por Deputado ===")
    try:
        resposta = auditor_ai(
            "Quais foram os gastos do deputado João Silva?",
            search_strategies={
                'lexical_deputado': 'João Silva',
                'semantic': True
            }
        )
        print(resposta)
    except Exception as e:
        print(f"Erro: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Exemplo 3: Análise de padrões
    print("=== Exemplo 3: Análise de Padrões ===")
    try:
        resposta = auditor_ai(
            "Quais outros deputados fizeram pagamentos para esta empresa?",
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
    except Exception as e:
        print(f"Erro: {e}")
