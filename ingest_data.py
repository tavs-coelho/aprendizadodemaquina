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
    
    # Create table with text and embedding columns
    # Note: Column names match what auditor_ai.py expects
    cursor.execute(f"""
        CREATE TABLE despesas_parlamentares (
            id SERIAL PRIMARY KEY,
            nome_deputado TEXT,
            cnpj_fornecedor TEXT,
            nome_fornecedor TEXT,
            descricao_despesa TEXT,
            valor NUMERIC,
            data_despesa DATE,
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
        CREATE INDEX IF NOT EXISTS despesas_parlamentares_embedding_idx 
        ON despesas_parlamentares 
        USING hnsw (descricao_embedding vector_cosine_ops);
    """)
    
    conn.commit()
    cursor.close()
    print("HNSW index created successfully.")


def sanitize_cnpj(cnpj_str):
    """
    Sanitize CNPJ by removing dots, dashes, and slashes.
    
    Args:
        cnpj_str: CNPJ string (may contain formatting)
    
    Returns:
        str: Sanitized CNPJ with only numbers
    """
    if pd.isna(cnpj_str) or not cnpj_str:
        return ""
    return str(cnpj_str).replace('.', '').replace('-', '').replace('/', '').strip()


def convert_valor(valor_str):
    """
    Convert valor (monetary value) from string to float.
    
    Handles various formats including comma as decimal separator.
    
    Args:
        valor_str: Value as string or number
    
    Returns:
        float: Converted value
    """
    if pd.isna(valor_str):
        return 0.0
    
    # If already numeric, return as float
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    # Convert string to float (handle comma as decimal separator)
    try:
        # Remove currency symbols and whitespace
        valor_clean = str(valor_str).replace('R$', '').replace(' ', '').strip()
        # Replace comma with dot for decimal
        valor_clean = valor_clean.replace(',', '.')
        return float(valor_clean)
    except (ValueError, AttributeError):
        return 0.0


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
        
        # Map CSV columns from ETL to database columns
        # ETL produces: nome, siglaPartido, txtFornecedor, cnpjCpfFornecedor, vlrLiquido, datEmissao
        deputado_nome = row.get('nome', row.get('deputado_nome', ''))
        fornecedor_nome = row.get('txtFornecedor', row.get('fornecedor_nome', ''))
        fornecedor_cnpj = sanitize_cnpj(row.get('cnpjCpfFornecedor', row.get('fornecedor_cnpj', '')))
        valor = convert_valor(row.get('vlrLiquido', row.get('valor', 0)))
        data = row.get('datEmissao', row.get('data', None))
        descricao = row.get('txtDescricao', '')
        
        # Insert data with column names matching auditor_ai.py expectations
        cursor.execute("""
            INSERT INTO despesas_parlamentares 
            (nome_deputado, cnpj_fornecedor, nome_fornecedor, 
             descricao_despesa, valor, data_despesa, descricao_embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            deputado_nome,
            fornecedor_cnpj,
            fornecedor_nome,
            descricao,
            valor,
            data,
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
            # Map CSV columns from ETL to database columns
            # ETL produces: nome, siglaPartido, txtFornecedor, cnpjCpfFornecedor, vlrLiquido, datEmissao
            deputado_nome = row.get('nome', row.get('deputado_nome', ''))
            deputado_partido = row.get('siglaPartido', row.get('deputado_partido', ''))
            fornecedor_nome = row.get('txtFornecedor', row.get('fornecedor_nome', ''))
            fornecedor_cnpj = sanitize_cnpj(row.get('cnpjCpfFornecedor', row.get('fornecedor_cnpj', '')))
            valor = convert_valor(row.get('vlrLiquido', row.get('valor', 0)))
            data = str(row.get('datEmissao', row.get('data', '')))
            descricao = row.get('txtDescricao', '')
            
            # Skip if CNPJ is empty (can't create unique Fornecedor node without it)
            if not fornecedor_cnpj:
                continue
            
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
                'deputado_nome': deputado_nome,
                'deputado_partido': deputado_partido,
                'fornecedor_nome': fornecedor_nome,
                'fornecedor_cnpj': fornecedor_cnpj,
                'valor': valor,
                'data': data,
                'descricao': descricao
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
    pg_conn = None
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
        
        print("✓ PostgreSQL operations completed")
        
    except Exception as e:
        print(f"✗ PostgreSQL error: {e}")
        raise
    finally:
        if pg_conn:
            pg_conn.close()
            print("✓ PostgreSQL connection closed")
    
    # Connect to Neo4j
    print("\nConnecting to Neo4j...")
    neo4j_driver = None
    try:
        neo4j_driver = get_neo4j_driver()
        print("✓ Connected to Neo4j")
        
        # Insert data into Neo4j
        insert_into_neo4j(df, neo4j_driver)
        
        print("✓ Neo4j operations completed")
        
    except Exception as e:
        print(f"✗ Neo4j error: {e}")
        raise
    finally:
        if neo4j_driver:
            neo4j_driver.close()
            print("✓ Neo4j connection closed")
    
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
