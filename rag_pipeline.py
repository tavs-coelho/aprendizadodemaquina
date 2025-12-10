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


def search_vector_neo4j(query_text, limit=10):
    """
    Search for similar vectors in Neo4j using OpenAI embeddings.
    
    Args:
        query_text (str): The text to search for
        limit (int): Maximum number of results to return (default: 10)
    
    Returns:
        list: List of nodes with similarity scores from Neo4j
    """
    # Load environment variables
    load_dotenv()
    
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
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError("Neo4j environment variables (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD) must be set")
    
    # Connect to Neo4j and query the vector index
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
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
    finally:
        driver.close()

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
