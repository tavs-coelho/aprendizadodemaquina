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


def search_hybrid_neo4j(text_query, graph_seed_title, limit=5):
    """
    Perform a hybrid search in Neo4j combining vector and keyword search.
    
    Args:
        text_query (str): The query text to search for
        graph_seed_title (str): The seed movie title to start the search from
        limit (int): Maximum number of results to return
        
    Returns:
        list: List of dictionaries containing movie information (title, plot)
    """
    # Load environment variables
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    # Create Neo4j driver
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    results = []
    
    try:
        with driver.session() as session:
            # Perform hybrid search: find movies related to the seed title
            # and matching the text query
            query = """
            MATCH (m:Movie)
            WHERE m.title CONTAINS $graph_seed_title 
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
    """
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
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.7)
    
    # Step 5: Build LangChain chain using the modern LCEL syntax
    chain = prompt | llm
    
    # Step 6: Generate and return the final answer
    response = chain.invoke({"context": context, "question": text_query})
    
    # Extract the content from the response
    if hasattr(response, 'content'):
        return response.content
    else:
        return str(response)


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
