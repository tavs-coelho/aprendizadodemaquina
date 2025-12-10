"""
Auditor AI - Sistema de RAG para Auditoria de Despesas Parlamentares

Este módulo implementa um sistema de Retrieval-Augmented Generation (RAG) 
para auditar despesas parlamentares usando múltiplas fontes de busca:
- Busca Lexical (SQL no Postgres)
- Busca Semântica (Vetorial no Postgres)
- Busca de Padrões (Grafos no Neo4j)
"""

import os
import logging
import hashlib
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


def search_lexical(query, search_type="deputado", limit=10):
    """
    Busca SQL no Postgres por nome de deputado ou fornecedor (CNPJ).
    
    Args:
        query (str): Nome do deputado ou CNPJ do fornecedor para buscar
        search_type (str): Tipo de busca - "deputado" ou "cnpj" (default: "deputado")
        limit (int): Número máximo de resultados (default: 10)
    
    Returns:
        list: Lista de dicionários contendo informações das despesas
    
    Raises:
        ValueError: Se as variáveis de ambiente do Postgres não estiverem configuradas
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


def search_semantic(query_text, limit=10):
    """
    Busca Vetorial no Postgres comparando a pergunta do usuário com a descrição da despesa.
    
    Utiliza embeddings do OpenAI para converter a pergunta em vetor e busca 
    similaridade com as descrições de despesas armazenadas.
    
    Args:
        query_text (str): Pergunta ou descrição a ser buscada (ex: 'aluguel de carros de luxo')
        limit (int): Número máximo de resultados (default: 10)
    
    Returns:
        list: Lista de dicionários contendo informações das despesas mais similares
    
    Raises:
        ValueError: Se as variáveis de ambiente não estiverem configuradas
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


def search_graph_patterns(query_type, param_value, limit=10):
    """
    Consulta o Neo4j para encontrar padrões nas despesas parlamentares.
    
    Args:
        query_type (str): Tipo de consulta - opções:
            - "fornecedor_deputados": Quais outros deputados pagaram este mesmo fornecedor?
            - "deputado_fornecedores": Quais fornecedores este deputado pagou?
            - "valor_alto": Deputados com despesas acima de um valor específico
        param_value: Valor do parâmetro (CNPJ para fornecedor, nome para deputado, valor para threshold)
        limit (int): Número máximo de resultados (default: 10)
    
    Returns:
        list: Lista de dicionários com padrões encontrados
    
    Raises:
        ValueError: Se as variáveis de ambiente do Neo4j não estiverem configuradas
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


def reciprocal_rank_fusion(search_results, k=60):
    """
    Aplica o algoritmo Reciprocal Rank Fusion (RRF) para combinar múltiplos resultados de busca.
    
    O RRF é uma técnica que combina rankings de diferentes métodos de busca,
    dando mais peso aos itens que aparecem bem ranqueados em múltiplas buscas.
    
    Args:
        search_results: Lista de listas, onde cada lista interna contém IDs de despesas
                       ranqueadas por relevância (primeiro elemento é rank 1)
        k: Constante para a fórmula RRF (default: 60)
    
    Returns:
        pandas.DataFrame com colunas 'despesa_id' e 'rrf_score',
        ordenado por rrf_score em ordem decrescente
    
    Formula:
        RRF_Score = ∑(1 / (k + rank_i)) para todos os resultados contendo a despesa
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


def format_expense_context(expenses):
    """
    Formata os dados de despesas em um contexto textual para o LLM.
    
    Args:
        expenses: Lista de dicionários contendo informações de despesas
    
    Returns:
        str: Contexto formatado em texto
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


def auditor_ai(user_question, search_strategies=None):
    """
    Sistema RAG completo para auditoria de despesas parlamentares.
    
    Combina diferentes estratégias de busca usando RRF e gera uma resposta
    usando LangChain com um prompt específico de Auditor Cidadão.
    
    Args:
        user_question (str): Pergunta do usuário sobre despesas parlamentares
        search_strategies (dict, optional): Dicionário com estratégias de busca a usar.
            Exemplo: {
                'lexical_deputado': 'Nome do Deputado',
                'lexical_cnpj': '12345678000190',
                'semantic': True,
                'graph_patterns': {'type': 'fornecedor_deputados', 'value': 'CNPJ'}
            }
            Se None, usa apenas busca semântica
    
    Returns:
        str: Resposta gerada pelo Auditor AI
    
    Raises:
        ValueError: Se OPENAI_API_KEY não estiver configurada
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
    system_prompt = """Você é um Auditor Cidadão Imparcial. 

Sua função é analisar despesas parlamentares e responder às perguntas dos cidadãos de forma objetiva e clara.

Use os dados recuperados das despesas parlamentares para responder à pergunta. 
Sempre cite:
- Valores específicos das despesas
- Nomes das empresas/fornecedores
- Datas das transações
- Nomes dos deputados envolvidos

Se identificar padrões suspeitos, aponte-os objetivamente:
- Valores muito altos para serviços genéricos
- Múltiplas transações com o mesmo fornecedor
- Descrições vagas ou genéricas com valores elevados
- Padrões incomuns de gastos

Seja factual, imparcial e baseie suas observações apenas nos dados apresentados."""

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
