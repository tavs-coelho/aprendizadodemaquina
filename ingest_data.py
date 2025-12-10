"""
Ingest Data Script for Despesas da Câmara
Reads despesas_camara.csv and populates Neo4j and PostgreSQL databases.
"""

import os
import pandas as pd
import psycopg2
from pgvector.psycopg2 import register_vector
from neo4j import GraphDatabase
import openai
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small model
BATCH_SIZE = 1000  # Number of rows to commit at once for PostgreSQL


def get_postgres_connection():
    """
    Create and return a PostgreSQL connection using environment variables.
    
    Returns:
        psycopg2 connection object
    """
    # Try Supabase first, then fall back to standard PostgreSQL
    supabase_url = os.getenv("SUPABASE_URL")
    
    if supabase_url:
        # Parse Supabase URL (format: https://xxxxx.supabase.co or db.xxxxx.supabase.co)
        # Extract host for database connection
        host = supabase_url.replace("https://", "").replace("http://", "")
        # Supabase database connections typically use db.{project-ref}.supabase.co format
        if not host.startswith("db."):
            # Convert project URL to database URL
            project_ref = host.split('.')[0]
            host = f"db.{project_ref}.supabase.co"
        
        conn = psycopg2.connect(
            host=host,
            port=os.getenv("SUPABASE_PORT", "5432"),
            database=os.getenv("SUPABASE_DB", "postgres"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD")
        )
    else:
        # Standard PostgreSQL connection
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "despesas_db"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
    
    return conn


def get_neo4j_driver():
    """
    Create and return a Neo4j driver using environment variables.
    
    Returns:
        Neo4j driver object
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError(
            "Missing Neo4j environment variables. "
            "Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD"
        )
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    return driver


def generate_embedding(text, client):
    """
    Generate embedding for text using OpenAI API.
    
    Args:
        text: Text to generate embedding for
        client: OpenAI client instance
        
    Returns:
        List of floats representing the embedding
    """
    if not text or pd.isna(text):
        text = ""
    
    try:
        response = client.embeddings.create(
            input=str(text),
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Return a zero vector of the expected dimension
        return [0.0] * EMBEDDING_DIMENSION


def setup_postgresql_table(conn):
    """
    Create the despesas_parlamentares table in PostgreSQL with pgvector extension.
    
    Args:
        conn: psycopg2 connection object
    """
    cursor = conn.cursor()
    
    # Enable pgvector extension
    print("Enabling pgvector extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Drop table if exists (for clean setup)
    print("Creating despesas_parlamentares table...")
    cursor.execute("DROP TABLE IF EXISTS despesas_parlamentares;")
    
    # Create table with text and embedding columns (matching auditor_ai.py expectations)
    cursor.execute(f"""
        CREATE TABLE despesas_parlamentares (
            id SERIAL PRIMARY KEY,
            nome_deputado TEXT,
            partido_deputado TEXT,
            nome_fornecedor TEXT,
            cnpj_fornecedor TEXT,
            valor NUMERIC,
            data_despesa DATE,
            descricao_despesa TEXT,
            descricao_embedding vector({EMBEDDING_DIMENSION})
        );
    """)
    
    conn.commit()
    cursor.close()
    print("Table created successfully.")


def create_hnsw_index(conn):
    """
    Create HNSW index for fast vector similarity search.
    
    Args:
        conn: psycopg2 connection object
    """
    cursor = conn.cursor()
    
    print("Creating HNSW index for vector search...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS despesas_embedding_idx 
        ON despesas_parlamentares 
        USING hnsw (descricao_embedding vector_cosine_ops);
    """)
    
    conn.commit()
    cursor.close()
    print("HNSW index created successfully.")


def insert_into_postgresql(df, conn, openai_client):
    """
    Insert data into PostgreSQL with embeddings.
    
    Args:
        df: Pandas DataFrame with despesas data
        conn: psycopg2 connection object
        openai_client: OpenAI client instance
    """
    cursor = conn.cursor()
    
    print("\nInserting data into PostgreSQL...")
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="PostgreSQL"):
        # Generate embedding for description
        embedding = generate_embedding(row.get('txtDescricao', ''), openai_client)
        
        # Insert data (matching auditor_ai.py expectations)
        cursor.execute("""
            INSERT INTO despesas_parlamentares 
            (nome_deputado, partido_deputado, nome_fornecedor, cnpj_fornecedor, 
             valor, data_despesa, descricao_despesa, descricao_embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row.get('nome', ''),  # ETL outputs 'nome'
            row.get('siglaPartido', ''),  # ETL outputs 'siglaPartido'
            row.get('txtFornecedor', ''),  # ETL outputs 'txtFornecedor'
            row.get('cnpjCpfFornecedor', ''),  # ETL outputs 'cnpjCpfFornecedor'
            row.get('vlrLiquido', 0),  # ETL outputs 'vlrLiquido'
            row.get('datEmissao', None),  # ETL outputs 'datEmissao'
            row.get('txtDescricao', ''),
            embedding
        ))
        
        # Commit every BATCH_SIZE rows for efficiency
        if (idx + 1) % BATCH_SIZE == 0:
            conn.commit()
    
    # Final commit
    conn.commit()
    cursor.close()
    print("PostgreSQL data insertion completed.")


def insert_into_neo4j(df, driver):
    """
    Insert data into Neo4j as nodes and relationships.
    
    Args:
        df: Pandas DataFrame with despesas data
        driver: Neo4j driver instance
    """
    print("\nInserting data into Neo4j...")
    
    with driver.session() as session:
        for idx, row in tqdm(df.iterrows(), total=len(df), desc="Neo4j"):
            # Use MERGE to avoid duplicates
            query = """
            MERGE (d:Deputado {nome: $deputado_nome})
            ON CREATE SET d.partido = $deputado_partido
            ON MATCH SET d.partido = $deputado_partido
            
            MERGE (f:Fornecedor {cnpj: $fornecedor_cnpj})
            ON CREATE SET f.nome = $fornecedor_nome
            ON MATCH SET f.nome = $fornecedor_nome
            
            CREATE (d)-[:PAGOU {
                valor: $valor,
                data: $data,
                descricao: $descricao
            }]->(f)
            """
            
            session.run(query, {
                'deputado_nome': row.get('nome', ''),  # ETL outputs 'nome'
                'deputado_partido': row.get('siglaPartido', ''),  # ETL outputs 'siglaPartido'
                'fornecedor_nome': row.get('txtFornecedor', ''),  # ETL outputs 'txtFornecedor'
                'fornecedor_cnpj': row.get('cnpjCpfFornecedor', ''),  # ETL outputs 'cnpjCpfFornecedor'
                'valor': float(row.get('vlrLiquido', 0)),  # ETL outputs 'vlrLiquido'
                'data': str(row.get('datEmissao', '')),  # ETL outputs 'datEmissao'
                'descricao': row.get('txtDescricao', '')
            })
    
    print("Neo4j data insertion completed.")


def main():
    """
    Main function to orchestrate the data ingestion process.
    """
    print("=" * 60)
    print("Despesas da Câmara - Data Ingestion Script")
    print("=" * 60)
    
    # Check for CSV file
    csv_file = "despesas_camara.csv"
    if not os.path.exists(csv_file):
        print(f"\nERROR: File '{csv_file}' not found!")
        print("Please ensure the CSV file exists in the current directory.")
        return
    
    # Validate environment variables
    print("\nValidating environment variables...")
    
    # Check OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    print("✓ OpenAI API key found")
    
    # Check Neo4j credentials
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_username = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        raise ValueError(
            "Missing Neo4j credentials. "
            "Please set NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD"
        )
    
    print("✓ Neo4j credentials found")
    
    # Check PostgreSQL credentials (either Supabase or standard PostgreSQL)
    supabase_url = os.getenv("SUPABASE_URL")
    postgres_host = os.getenv("POSTGRES_HOST")
    
    if not supabase_url and not postgres_host:
        raise ValueError(
            "Missing PostgreSQL credentials. "
            "Please set either SUPABASE_URL or POSTGRES_HOST"
        )
    
    print("✓ PostgreSQL credentials found")
    
    # Read CSV file
    print(f"\nReading CSV file: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"✓ Loaded {len(df)} records")
    
    # Display sample data
    print("\nSample data (first 3 rows):")
    print(df.head(3))
    
    # Initialize OpenAI client
    print("\nInitializing OpenAI client...")
    openai_client = openai.OpenAI(api_key=openai_api_key)
    print("✓ OpenAI client initialized")
    
    # Connect to PostgreSQL
    print("\nConnecting to PostgreSQL...")
    try:
        pg_conn = get_postgres_connection()
        register_vector(pg_conn)
        print("✓ Connected to PostgreSQL")
        
        # Setup PostgreSQL table
        setup_postgresql_table(pg_conn)
        
        # Insert data into PostgreSQL
        insert_into_postgresql(df, pg_conn, openai_client)
        
        # Create HNSW index
        create_hnsw_index(pg_conn)
        
        pg_conn.close()
        print("✓ PostgreSQL connection closed")
        
    except Exception as e:
        print(f"✗ PostgreSQL error: {e}")
        raise
    
    # Connect to Neo4j
    print("\nConnecting to Neo4j...")
    try:
        neo4j_driver = get_neo4j_driver()
        print("✓ Connected to Neo4j")
        
        # Insert data into Neo4j
        insert_into_neo4j(df, neo4j_driver)
        
        neo4j_driver.close()
        print("✓ Neo4j connection closed")
        
    except Exception as e:
        print(f"✗ Neo4j error: {e}")
        raise
    
    print("\n" + "=" * 60)
    print("Data ingestion completed successfully!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Records processed: {len(df)}")
    print(f"  - PostgreSQL: Table 'despesas_parlamentares' populated with embeddings")
    print(f"  - Neo4j: Nodes and relationships created")
    print("=" * 60)


if __name__ == "__main__":
    main()
