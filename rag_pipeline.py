"""
RAG Pipeline - Main file
This module implements a Retrieval-Augmented Generation pipeline.
"""

import os
import pandas as pd
from neo4j import GraphDatabase
import openai
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

def search_graph_actors(movie_title, limit=10):
    """
    Finds movies related to movie_title by shared actors (collaborative recommendation).
    
    Args:
        movie_title: The title of the movie to find recommendations for
        limit: Maximum number of recommendations to return (default: 10)
        
    Returns:
        List of dictionaries with movieId, title, and score (count of common actors)
    """
    # Get Neo4j connection details from environment
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        missing = []
        if not neo4j_uri:
            missing.append("NEO4J_URI")
        if not neo4j_user:
            missing.append("NEO4J_USERNAME")
        if not neo4j_password:
            missing.append("NEO4J_PASSWORD")
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    # Create Neo4j driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Cypher query to find movies sharing actors with the input movie
            query = """
            MATCH (m:Movie {title: $movie_title})<-[:ACTED_IN]-(a:Actor)
            MATCH (a)-[:ACTED_IN]->(rec:Movie)
            WHERE m.movieId <> rec.movieId
            WITH rec.movieId AS movieId, rec.title AS title, COUNT(DISTINCT a) AS score
            RETURN movieId, title, score
            ORDER BY score DESC
            LIMIT $limit
            """
            
            result = session.run(query, movie_title=movie_title, limit=limit)
            
            # Convert result to list of dictionaries
            recommendations = []
            for record in result:
                recommendations.append({
                    'movieId': record['movieId'],
                    'title': record['title'],
                    'score': record['score']
                })
            
            return recommendations
    finally:
        driver.close()

def search_vector_neo4j(query_text, limit=10):
    """
    Search for similar vectors in Neo4j using OpenAI embeddings.
    
    Args:
        query_text (str): The text to search for
        limit (int): Maximum number of results to return (default: 10)
    
    Returns:
        list: List of nodes with similarity scores from Neo4j
    """
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)
    
    # Generate embedding for the query text using text-embedding-3-small
    response = client.embeddings.create(
        input=query_text,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding
    
    # Get Neo4j connection details
# RAG Prompt Template
RAG_PROMPT_TEMPLATE = """Você é um especialista em recomendação de filmes. Sua função é ajudar os usuários a encontrar filmes que correspondam aos seus interesses e preferências.

Use o contexto fornecido abaixo para responder à pergunta do usuário de forma precisa e útil. Se o contexto não contiver informações suficientes para responder à pergunta, seja honesto e indique isso ao usuário.

Contexto:
{context}

Pergunta do usuário:
{question}

Resposta:"""


def search_hybrid_neo4j(text_query, graph_seed_title, limit=5):
    """
    Perform a keyword-based search in Neo4j for movies.
    
    Args:
        text_query (str): The query text to search for
        graph_seed_title (str): The seed movie title to start the search from
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing movie information (title, plot)
        
    Raises:
        ValueError: If required environment variables are not set
    """
    # Load environment variables
def reciprocal_rank_fusion(ranked_lists, k=60):
    """
    Combines multiple ranked lists using Reciprocal Rank Fusion.
    
    Args:
        ranked_lists: List of lists containing movieIds in ranked order
        k: Constant for RRF formula (default=60)
    
    Returns:
        List of movieIds sorted by fused score (descending)
    """
    scores = {}
    
    for ranked_list in ranked_lists:
        for rank, movie_id in enumerate(ranked_list, start=1):
            if movie_id not in scores:
                scores[movie_id] = 0
            scores[movie_id] += 1 / (k + rank)
    
    # Sort by score descending
    fused_ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [movie_id for movie_id, score in fused_ranking]


def search_lexical_neo4j(text_query, k=10):
    """
    Performs lexical (full-text) search in Neo4j.
    
    Args:
        text_query: Text query string
        k: Number of results to return (default=10)
    
    Returns:
        List of movieIds
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError("Neo4j environment variables (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) must be set")
    
    # Connect to Neo4j and query the vector index
    with GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password)) as driver:
        with driver.session() as session:
            # Query the movieVectorIndex using cosine similarity
            result = session.run(
                """
                CALL db.index.vector.queryNodes('movieVectorIndex', $limit, $embedding)
                YIELD node, score
                RETURN node, score
                """,
                embedding=query_embedding,
                limit=limit
            )
            
            # Collect results
            results = []
            for record in result:
                results.append({
                    'node': record['node'],
                    'score': record['score']
                })
            
            return results
    # Validate required environment variables
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError(
            "Missing required Neo4j environment variables. "
            "Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD."
        )
    
    # Create Neo4j driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    results = []
    
    try:
        with driver.session() as session:
            # Perform keyword search: find movies related to the seed title
            # and matching the text query
            query = """
            MATCH (m:Movie)
            WHERE toLower(m.title) CONTAINS toLower($graph_seed_title)
               OR toLower(m.plot) CONTAINS toLower($text_query)
               OR toLower(m.title) CONTAINS toLower($text_query)
            RETURN m.title AS title, m.plot AS plot
            LIMIT $limit
            """
            
            result = session.run(query, 
                               graph_seed_title=graph_seed_title,
                               text_query=text_query,
                               limit=limit)
            
            for record in result:
                results.append({
                    'title': record['title'],
                    'plot': record['plot']
                })
    finally:
        driver.close()
    
    return results


def answer_question_with_rag(text_query, graph_seed_title):
    """
    Answer a question using Retrieval-Augmented Generation (RAG).
    
    This function:
    1. Calls search_hybrid_neo4j to retrieve relevant movies
    2. Formats movie data (title, plot) into a context string
    3. Uses ChatOpenAI with gpt-4o-mini model and a prompt template
    4. Generates the final answer using LangChain
    
    Args:
        text_query (str): The question to answer
        graph_seed_title (str): The seed movie title for graph search
        
    Returns:
        str: The generated answer
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set in environment variables
    """
    # Validate OpenAI API key is available
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY environment variable. "
            "Please set OPENAI_API_KEY to use the ChatOpenAI model."
        )
    
    # Step 1: Call search_hybrid_neo4j to retrieve relevant movies
    movies = search_hybrid_neo4j(text_query, graph_seed_title)
    
    # Step 2: Format movie data into a context string
    context_parts = []
    for movie in movies:
        title = movie.get('title', 'Unknown')
        plot = movie.get('plot', 'No plot available')
        context_parts.append(f"Título: {title}\nEnredo: {plot}")
    
    context = "\n\n".join(context_parts)
    
    # Step 3: Create prompt template
    template = """Você é um assistente especializado em filmes. Use o contexto fornecido abaixo para responder à pergunta do usuário.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
    
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=template
    )
    
    # Step 4: Set up ChatOpenAI with gpt-4o-mini model
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.7, api_key=openai_api_key)
    
    # Step 5: Build LangChain chain using the modern LCEL syntax
    chain = prompt | llm
    
    # Step 6: Generate and return the final answer
    response = chain.invoke({"context": context, "question": text_query})
    
    # Extract the content from the response
    if hasattr(response, 'content'):
        return response.content
    else:
        return str(response)
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
        with driver.session() as session:
            query = """
            CALL db.index.fulltext.queryNodes('movieTitleIndex', $text_query)
            YIELD node, score
            RETURN node.movieId AS movieId
            LIMIT $k
            """
            result = session.run(query, text_query=text_query, k=k)
            movie_ids = [record["movieId"] for record in result]
            return movie_ids
    finally:
        driver.close()


def search_vectorial_neo4j(text_query, k=10):
    """
    Performs vector similarity search in Neo4j.
    
    Args:
        text_query: Text query string
        k: Number of results to return (default=10)
    
    Returns:
        List of movieIds
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
        # Get embedding for query using OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text_query
        )
        query_embedding = response.data[0].embedding
        
        with driver.session() as session:
            query = """
            CALL db.index.vector.queryNodes('movieEmbeddingIndex', $k, $embedding)
            YIELD node, score
            RETURN node.movieId AS movieId
            """
            result = session.run(query, k=k, embedding=query_embedding)
            movie_ids = [record["movieId"] for record in result]
            return movie_ids
    finally:
        driver.close()


def search_graph_neo4j(graph_seed_title, k=10):
    """
    Performs graph-based search in Neo4j starting from a seed movie title.
    
    Args:
        graph_seed_title: Title of the seed movie for graph traversal
        k: Number of results to return (default=10)
    
    Returns:
        List of movieIds
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
        with driver.session() as session:
            query = """
            MATCH (seed:Movie {title: $seed_title})
            MATCH (seed)-[:SIMILAR_TO|HAS_GENRE|HAS_ACTOR|HAS_DIRECTOR*1..2]-(related:Movie)
            WHERE seed.movieId <> related.movieId
            RETURN DISTINCT related.movieId AS movieId
            LIMIT $k
            """
            result = session.run(query, seed_title=graph_seed_title, k=k)
            movie_ids = [record["movieId"] for record in result]
            return movie_ids
    finally:
        driver.close()


def search_hybrid_neo4j(text_query, graph_seed_title, k=10):
    """
    Performs hybrid search combining lexical, vectorial, and graph-based searches.
    
    Args:
        text_query: Text query string for lexical and vectorial search
        graph_seed_title: Title of the seed movie for graph-based search
        k: Number of results to return from each search method (default=10)
    
    Returns:
        List of movieIds sorted by fused ranking score
    """
    # Call the three search functions with error handling
    ranked_lists = []
    
    try:
        lexical_results = search_lexical_neo4j(text_query, k)
        ranked_lists.append(lexical_results)
    except Exception as e:
        print(f"Warning: Lexical search failed: {e}")
    
    try:
        vectorial_results = search_vectorial_neo4j(text_query, k)
        ranked_lists.append(vectorial_results)
    except Exception as e:
        print(f"Warning: Vectorial search failed: {e}")
    
    try:
        graph_results = search_graph_neo4j(graph_seed_title, k)
        ranked_lists.append(graph_results)
    except Exception as e:
        print(f"Warning: Graph search failed: {e}")
    
    # Combine results using reciprocal rank fusion
    fused_ranking = reciprocal_rank_fusion(ranked_lists)
    
    return fused_ranking


# Load environment variables
if __name__ == "__main__":
    # Load environment variables from .env file if needed
    load_dotenv()
    
    # Environment variables can be accessed using os.getenv()
    # Example:
    # openai_api_key = os.getenv("OPENAI_API_KEY")
    # neo4j_uri = os.getenv("NEO4J_URI")
    # neo4j_user = os.getenv("NEO4J_USER")
    # neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    print("RAG Pipeline initialized successfully")
