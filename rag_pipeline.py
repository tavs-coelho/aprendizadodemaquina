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


def reciprocal_rank_fusion(search_results, k=60):
    """
    Applies Reciprocal Rank Fusion (RRF) to combine multiple search results.
    
    Args:
        search_results: A list of lists, where each inner list contains movie_ids
                       ranked by relevance (first element is rank 1).
        k: A constant parameter for the RRF formula (default: 60).
    
    Returns:
        A pandas DataFrame with columns 'movie_id' and 'rrf_score', 
        sorted by rrf_score in descending order.
    
    Formula:
        RRF_Score = ∑(1 / (k + rank_i)) for all search results containing the movie
    """
    # Dictionary to accumulate RRF scores for each movie_id
    rrf_scores = {}
    
    # Iterate through each search result list
    for search_result in search_results:
        # Iterate through each movie in the search result with its rank (1-indexed)
        for rank, movie_id in enumerate(search_result, start=1):
            # Calculate the contribution to RRF score for this movie in this search result
            score_contribution = 1 / (k + rank)
            
            # Add the contribution to the movie's total RRF score
            if movie_id in rrf_scores:
                rrf_scores[movie_id] += score_contribution
            else:
                rrf_scores[movie_id] = score_contribution
    
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(list(rrf_scores.items()), columns=['movie_id', 'rrf_score'])
    
    # Sort by rrf_score in descending order
    df = df.sort_values(by='rrf_score', ascending=False).reset_index(drop=True)
    
    return df

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
