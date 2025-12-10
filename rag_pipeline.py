"""
RAG Pipeline - Main file
This module implements a Retrieval-Augmented Generation pipeline.
"""

import os
import pandas as pd
from neo4j import GraphDatabase
import openai
from langchain_openai import ChatOpenAI
from sqlalchemy import create_engine
from dotenv import load_dotenv


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
    # Call the three search functions
    lexical_results = search_lexical_neo4j(text_query, k)
    vectorial_results = search_vectorial_neo4j(text_query, k)
    graph_results = search_graph_neo4j(graph_seed_title, k)
    
    # Combine results using reciprocal rank fusion
    ranked_lists = [lexical_results, vectorial_results, graph_results]
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
