"""
RAG Pipeline - Main file
This module implements a Retrieval-Augmented Generation pipeline.
"""

import os
import pandas as pd
from neo4j import GraphDatabase
import openai
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy import create_engine
from dotenv import load_dotenv
import chromadb


def index_documents(pdf_path, chunk_size=1000):
    """
    Processes a PDF document and stores its chunks in a local vector database.
    
    Args:
        pdf_path: Path to the PDF file to process
        chunk_size: Size of text chunks for splitting (default=1000)
    
    Returns:
        FAISS vector store containing the indexed document chunks
    
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
        FileNotFoundError: If the PDF file does not exist
    """
    # Validate PDF file exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Check for OpenAI API key
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
            rrf_scores[movie_id] = rrf_scores.get(movie_id, 0) + score_contribution
    
    # Convert the dictionary to a DataFrame
    df = pd.DataFrame(list(rrf_scores.items()), columns=['movie_id', 'rrf_score'])
    
    # Sort by rrf_score in descending order
    df = df.sort_values(by='rrf_score', ascending=False).reset_index(drop=True)
    
    return df
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
    
    # Load the PDF document using PyPDFLoader
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # Split the documents into chunks using RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=200,  # Add overlap to maintain context between chunks
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    
    # Create embeddings using OpenAI (automatically uses OPENAI_API_KEY env var)
    embeddings = OpenAIEmbeddings()
    
    # Create and populate FAISS vector store
    vectorstore = FAISS.from_documents(chunks, embeddings)
    
    return vectorstore


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


def search_document_vector(query_text, k=3):
    """
    Performs vector similarity search in the document index (ChromaDB) created.
    
    Args:
        query_text (str): The text query to search for
        k (int): Number of most similar results to return (default=3)
    
    Returns:
        list: List of dictionaries containing metadata and content of matched chunks.
              Each dictionary has the following structure:
              {
                  'content': str,  # The text content of the chunk
                  'metadata': dict,  # Associated metadata
                  'distance': float  # Similarity distance
              }
    
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
        RuntimeError: If ChromaDB collection is not found or other database errors occur
    """
    # Validate OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "Missing OPENAI_API_KEY environment variable. "
            "Please set OPENAI_API_KEY to generate embeddings."
        )
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)
    
    # Generate embedding for the query text
    try:
        response = client.embeddings.create(
            input=query_text,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
    except Exception as e:
        raise RuntimeError(
            f"Failed to generate embeddings using OpenAI API. "
            f"Please check your API key and network connection. Error: {e}"
        )
    
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        # Get existing collection for documents
        collection = chroma_client.get_collection(name="documents")
    except ValueError as e:
        # ChromaDB raises ValueError when collection doesn't exist
        raise RuntimeError(
            f"ChromaDB collection 'documents' not found. "
            f"Make sure the collection exists and is properly initialized. Error: {e}"
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to access ChromaDB collection 'documents'. Error: {e}"
        )
    
    # Perform similarity search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )
    
    # Format results
    formatted_results = []
    
    if results['documents'] and len(results['documents']) > 0:
        documents = results['documents'][0]  # First query result
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(documents)
        distances = results['distances'][0] if results.get('distances') else [0.0] * len(documents)
        
        for i in range(len(documents)):
            formatted_results.append({
                'content': documents[i],
                'metadata': metadatas[i] if i < len(metadatas) else {},
                'distance': distances[i] if i < len(distances) else 0.0
            })
    
    return formatted_results
def get_movie_details(movie_ids):
    """
    Retrieves movie details (title, plot) from Neo4j for given movie IDs.
    
    Args:
        movie_ids: List of movieIds to retrieve details for
    
    Returns:
        List of dictionaries containing movie details (title, plot)
    """
    if not movie_ids:
        return []
    
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError("Neo4j connection environment variables are not properly set")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
        with driver.session() as session:
            query = """
            MATCH (m:Movie)
            WHERE m.movieId IN $movie_ids
            RETURN m.title AS title, m.plot AS plot, m.movieId AS movieId
            """
            result = session.run(query, movie_ids=movie_ids)
            movies = [{"title": record["title"], "plot": record["plot"], "movieId": record["movieId"]} 
                      for record in result]
            return movies
    finally:
        driver.close()


def answer_question_with_rag(text_query, graph_seed_title):
    """
    Answers a question using Retrieval-Augmented Generation (RAG).
    
    This function:
    1. Calls search_hybrid_neo4j to retrieve relevant movie IDs
    2. Retrieves movie details (title, plot) from Neo4j
    3. Formats the movie data into a context string
    4. Uses ChatOpenAI with gpt-4o-mini model and a prompt template
    5. Builds a LangChain chain to generate the final answer
    
    Args:
        text_query: Text query string for the question
        graph_seed_title: Title of the seed movie for graph-based search
    
    Returns:
        String containing the generated answer
    """
    # Step 1: Call search_hybrid_neo4j to get relevant movie IDs
    movie_ids = search_hybrid_neo4j(text_query, graph_seed_title, k=10)
    
    # Check if search returned any results
    if not movie_ids:
        return "Desculpe, não encontrei filmes relevantes para sua pergunta."
    
    # Step 2: Retrieve movie details for the returned IDs
    movies = get_movie_details(movie_ids)
    
    # Check if movie details were retrieved
    if not movies:
        return "Desculpe, não consegui recuperar informações sobre os filmes encontrados."
    
    # Step 3: Format movie data into a context string
    context = ""
    for movie in movies:
        title = movie.get("title", "Unknown")
        plot = movie.get("plot", "No plot available")
        context += f"Título: {title}\nEnredo: {plot}\n\n"
    
    # Step 4: Create prompt template for RAG
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""Você é um assistente especializado em filmes. Use o contexto fornecido abaixo para responder à pergunta do usuário de forma precisa e informativa.

Contexto dos filmes:
{context}

Pergunta: {question}

Resposta:"""
    )
    
    # Step 5: Initialize ChatOpenAI with gpt-4o-mini model
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.7, openai_api_key=openai_api_key)
    
    # Step 6: Build LangChain chain using LCEL (LangChain Expression Language)
    output_parser = StrOutputParser()
    chain = prompt_template | llm | output_parser
    
    # Step 7: Generate and return final answer
    response = chain.invoke({"context": context, "question": text_query})
    
    return response


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
