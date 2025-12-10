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

# RAG Prompt Template
RAG_PROMPT_TEMPLATE = """Você é um especialista em recomendação de filmes. Sua função é ajudar os usuários a encontrar filmes que correspondam aos seus interesses e preferências.

Use o contexto fornecido abaixo para responder à pergunta do usuário de forma precisa e útil. Se o contexto não contiver informações suficientes para responder à pergunta, seja honesto e indique isso ao usuário.

Contexto:
{context}

Pergunta do usuário:
{question}

Resposta:"""

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
