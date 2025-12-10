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
