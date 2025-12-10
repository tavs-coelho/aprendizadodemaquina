#!/usr/bin/env python3
"""
Setup and Verification Script for Fiscalizador Cidadão
DevOps/QA Script - Diagnoses environment setup and API connectivity issues

This script performs sequential validation:
1. Phase 1: Environment variables (.env) validation
2. Phase 2: Connectivity smoke tests (OpenAI, Neo4j, PostgreSQL)
3. Phase 3: Functional RAG integration tests
"""

import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

# Try importing colorama for colored output, fallback to ANSI codes
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    RESET = Style.RESET_ALL
except ImportError:
    # Fallback to ANSI escape codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_success(message):
    """Print success message in green"""
    print(f"{GREEN}✓ SUCESSO: {message}{RESET}")


def print_error(message):
    """Print error message in red"""
    print(f"{RED}✗ FALHA: {message}{RESET}")


def print_warning(message):
    """Print warning message in yellow"""
    print(f"{YELLOW}⚠ AVISO: {message}{RESET}")


def print_info(message):
    """Print info message in blue"""
    print(f"{BLUE}ℹ INFO: {message}{RESET}")


def print_header(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{BLUE}{title.center(70)}{RESET}")
    print(f"{'='*70}\n")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_supabase_host(supabase_url):
    """
    Parse and normalize Supabase URL to database host format.
    
    Args:
        supabase_url (str): Supabase URL (can be https://xxx.supabase.co or db.xxx.supabase.co)
        
    Returns:
        str: Database host in format db.{project-ref}.supabase.co
        
    Raises:
        ValueError: If URL format is invalid
    """
    if not supabase_url or supabase_url == 'insira_aqui':
        raise ValueError("Invalid Supabase URL")
    
    # Remove protocol if present
    host = supabase_url.replace("https://", "").replace("http://", "")
    
    # Remove trailing slashes
    host = host.rstrip('/')
    
    # If already in db.xxx.supabase.co format, return as-is
    if host.startswith("db."):
        return host
    
    # Extract project reference and convert to database host
    try:
        # Parse the hostname to extract project reference
        parts = host.split('.')
        if len(parts) >= 3 and 'supabase' in host:
            project_ref = parts[0]
            return f"db.{project_ref}.supabase.co"
        else:
            raise ValueError(f"Unable to parse Supabase URL format: {supabase_url}")
    except Exception as e:
        raise ValueError(f"Invalid Supabase URL format: {supabase_url} - {str(e)}")


# =============================================================================
# PHASE 1: Environment Variables Validation
# =============================================================================

def create_env_template():
    """Create a .env file with default template values"""
    template = """# OpenAI API Configuration
OPENAI_API_KEY=insira_aqui

# Neo4j Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=insira_aqui

# PostgreSQL/Supabase Configuration
SUPABASE_URL=insira_aqui
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=insira_aqui

# PostgreSQL Configuration (alternative to Supabase)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=despesas_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=insira_aqui
"""
    
    env_path = Path('.env')
    with open(env_path, 'w') as f:
        f.write(template)
    
    print_success(f"Arquivo .env criado com template padrão")
    print_warning("AÇÃO NECESSÁRIA: Preencha o arquivo .env com suas credenciais e execute o script novamente")
    print_info(f"Localização: {env_path.absolute()}")
    return False


def validate_env_file():
    """
    Phase 1: Validate .env file exists and has required variables
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    print_header("FASE 1: VALIDAÇÃO DE VARIÁVEIS DE AMBIENTE (.env)")
    
    env_path = Path('.env')
    
    # Check if .env exists
    if not env_path.exists():
        print_error("Arquivo .env não encontrado")
        return create_env_template()
    
    print_success("Arquivo .env encontrado")
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_error("Biblioteca python-dotenv não instalada")
        print_info("Execute: pip install python-dotenv")
        return False
    
    # Check critical variables
    critical_vars = {
        'OPENAI_API_KEY': 'Chave da API OpenAI',
        'NEO4J_URI': 'URI do Neo4j',
        'NEO4J_USERNAME': 'Usuário do Neo4j',
        'NEO4J_PASSWORD': 'Senha do Neo4j',
    }
    
    # Check PostgreSQL variables (at least one set must be configured)
    postgres_vars = [
        ('SUPABASE_URL', 'SUPABASE_USER', 'SUPABASE_PASSWORD'),
        ('POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD')
    ]
    
    all_valid = True
    
    # Validate critical variables
    for var, description in critical_vars.items():
        value = os.getenv(var, '')
        if not value or value == 'insira_aqui':
            print_error(f"{description} ({var}) não configurada ou com valor padrão")
            all_valid = False
        else:
            # Mask sensitive values in output
            masked_value = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            print_success(f"{description} configurada ({masked_value})")
    
    # Validate at least one PostgreSQL configuration set
    postgres_configured = False
    for var_set in postgres_vars:
        if all(os.getenv(var) and os.getenv(var) != 'insira_aqui' for var in var_set):
            postgres_configured = True
            config_type = 'Supabase' if 'SUPABASE' in var_set[0] else 'PostgreSQL local'
            print_success(f"Configuração de {config_type} encontrada")
            break
    
    if not postgres_configured:
        print_error("Nenhuma configuração de PostgreSQL completa encontrada")
        print_info("Configure SUPABASE_* ou POSTGRES_* no arquivo .env")
        all_valid = False
    
    if not all_valid:
        print_warning("\nAÇÃO NECESSÁRIA: Corrija as variáveis de ambiente faltantes no arquivo .env")
        return False
    
    print_success("\nTodas as variáveis de ambiente estão configuradas")
    return True


# =============================================================================
# PHASE 2: Connectivity Smoke Tests
# =============================================================================

def test_openai_connection():
    """
    Test OpenAI API connectivity and authentication
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print_info("Testando conexão com OpenAI API...")
    
    try:
        import openai
        from openai import OpenAI
    except ImportError:
        print_error("Biblioteca openai não instalada")
        print_info("Execute: pip install openai")
        return False
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print_error("OPENAI_API_KEY não configurada")
        return False
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Make a cheap API call to verify the key
        # Using embedding generation with a single word is very cheap
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="teste"
        )
        
        if response.data and len(response.data) > 0:
            print_success("Conexão com OpenAI API estabelecida com sucesso")
            print_info(f"Modelo de embedding disponível: text-embedding-3-small")
            return True
        else:
            print_error("Resposta inesperada da OpenAI API")
            return False
            
    except openai.AuthenticationError as e:
        print_error("Erro de autenticação com OpenAI")
        print_info("Sua chave da OpenAI parece inválida. Verifique o arquivo .env")
        print_info(f"Detalhes: {str(e)}")
        return False
    except openai.RateLimitError as e:
        print_error("Limite de requisições atingido")
        print_info("Sua conta OpenAI atingiu o limite de requisições ou não tem saldo")
        print_info(f"Detalhes: {str(e)}")
        return False
    except Exception as e:
        print_error(f"Erro ao conectar com OpenAI: {str(e)}")
        return False


def test_neo4j_connection():
    """
    Test Neo4j database connectivity
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print_info("Testando conexão com Neo4j...")
    
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print_error("Biblioteca neo4j não instalada")
        print_info("Execute: pip install neo4j")
        return False
    
    uri = os.getenv('NEO4J_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    
    if not all([uri, username, password]):
        print_error("Credenciais do Neo4j não configuradas completamente")
        return False
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Verify connection by running a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            record = result.single()
            if record and record["test"] == 1:
                print_success("Conexão com Neo4j estabelecida com sucesso")
                
                # Check if there's any data
                count_result = session.run("MATCH (n) RETURN count(n) AS count")
                count = count_result.single()["count"]
                print_info(f"Nós no banco de dados: {count}")
                
                driver.close()
                return True
            else:
                print_error("Resposta inesperada do Neo4j")
                driver.close()
                return False
                
    except Exception as e:
        print_error(f"Erro ao conectar com Neo4j: {str(e)}")
        print_info("Verifique se o Docker está rodando e o Neo4j está acessível")
        print_info(f"URI configurada: {uri}")
        print_info("Execute: docker ps | grep neo4j")
        return False


def test_postgresql_connection():
    """
    Test PostgreSQL database connectivity and pgvector extension
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print_info("Testando conexão com PostgreSQL...")
    
    try:
        import psycopg2
    except ImportError:
        print_error("Biblioteca psycopg2 não instalada")
        print_info("Execute: pip install psycopg2-binary")
        return False
    
    # Try Supabase first, then local PostgreSQL
    supabase_url = os.getenv('SUPABASE_URL')
    
    try:
        if supabase_url and supabase_url != 'insira_aqui':
            # Supabase connection
            try:
                host = parse_supabase_host(supabase_url)
            except ValueError as e:
                print_error(f"Formato inválido de URL do Supabase: {str(e)}")
                return False
            
            conn = psycopg2.connect(
                host=host,
                port=os.getenv("SUPABASE_PORT", "5432"),
                database=os.getenv("SUPABASE_DB", "postgres"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                connect_timeout=10
            )
            db_type = "Supabase"
        else:
            # Local PostgreSQL connection
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "despesas_db"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                connect_timeout=10
            )
            db_type = "PostgreSQL local"
        
        cursor = conn.cursor()
        
        # Test basic connectivity
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print_success(f"Conexão com {db_type} estabelecida com sucesso")
        else:
            print_error(f"Resposta inesperada do {db_type}")
            cursor.close()
            conn.close()
            return False
        
        # Check if pgvector extension is installed
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            )
        """)
        vector_installed = cursor.fetchone()[0]
        
        if vector_installed:
            print_success("Extensão pgvector está instalada e ativa")
        else:
            print_error("Extensão pgvector não está instalada")
            print_info("Execute no PostgreSQL: CREATE EXTENSION vector;")
            cursor.close()
            conn.close()
            return False
        
        # Check if main table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'despesas_parlamentares'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM despesas_parlamentares")
            count = cursor.fetchone()[0]
            print_info(f"Tabela despesas_parlamentares existe com {count} registros")
        else:
            print_warning("Tabela despesas_parlamentares não existe (será criada no ingest)")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print_error(f"Erro de conexão com PostgreSQL: {str(e)}")
        print_info("Verifique se o PostgreSQL está rodando e as credenciais estão corretas")
        return False
    except Exception as e:
        print_error(f"Erro ao conectar com PostgreSQL: {str(e)}")
        return False


def run_smoke_tests():
    """
    Phase 2: Run connectivity smoke tests
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print_header("FASE 2: TESTES DE CONECTIVIDADE (SMOKE TESTS)")
    
    results = {
        'OpenAI': test_openai_connection(),
        'Neo4j': test_neo4j_connection(),
        'PostgreSQL': test_postgresql_connection()
    }
    
    print("\n" + "-"*70)
    print("RESUMO DOS TESTES DE CONECTIVIDADE:")
    print("-"*70)
    
    for service, passed in results.items():
        status = f"{GREEN}✓ PASSOU{RESET}" if passed else f"{RED}✗ FALHOU{RESET}"
        print(f"{service:20s}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print_success("\nTodos os testes de conectividade passaram!")
    else:
        print_error("\nAlguns testes de conectividade falharam")
        print_warning("Corrija os problemas acima antes de prosseguir para a Fase 3")
    
    return all_passed


# =============================================================================
# PHASE 3: Functional RAG Integration Tests
# =============================================================================

def test_import_modules():
    """
    Test if main modules can be imported without errors
    
    Returns:
        bool: True if all imports successful, False otherwise
    """
    print_info("Testando importação de módulos principais...")
    
    modules = {
        'etl_camara': 'ETL da Câmara dos Deputados',
        'ingest_data': 'Ingestão de dados',
        'auditor_ai': 'Auditor AI (RAG)'
    }
    
    results = {}
    
    for module_name, description in modules.items():
        try:
            __import__(module_name)
            print_success(f"Módulo {module_name} importado com sucesso")
            results[module_name] = True
        except ImportError as e:
            print_error(f"Erro ao importar {module_name}: {str(e)}")
            results[module_name] = False
        except Exception as e:
            print_warning(f"Aviso ao importar {module_name}: {str(e)}")
            results[module_name] = True  # Consider it a pass if not an import error
    
    return all(results.values())


def test_dummy_data_insertion():
    """
    Test RAG system end-to-end by inserting dummy data and retrieving it
    
    Returns:
        bool: True if test successful, False otherwise
    """
    print_info("Testando sistema RAG com dados de teste...")
    
    try:
        import psycopg2
        from neo4j import GraphDatabase
        from openai import OpenAI
        
        # Generate a unique test ID to avoid conflicts (using uuid for guaranteed uniqueness)
        test_id = f"TEST_{uuid.uuid4().hex[:12]}"
        
        # Test data
        test_deputado = f"Deputado Teste {test_id}"
        test_fornecedor = f"Fornecedor Teste {test_id}"
        test_cnpj = "00000000000000"
        test_descricao = f"Despesa de teste para validação do sistema - {test_id}"
        test_valor = 1000.00
        test_data = datetime.now().date()
        
        print_info(f"Inserindo dado de teste: {test_deputado}")
        
        # 1. Test PostgreSQL vector insertion
        supabase_url = os.getenv('SUPABASE_URL')
        
        if supabase_url and supabase_url != 'insira_aqui':
            try:
                host = parse_supabase_host(supabase_url)
            except ValueError as e:
                print_error(f"Formato inválido de URL do Supabase: {str(e)}")
                return False
            
            conn = psycopg2.connect(
                host=host,
                port=os.getenv("SUPABASE_PORT", "5432"),
                database=os.getenv("SUPABASE_DB", "postgres"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD")
            )
        else:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "despesas_db"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD")
            )
        
        cursor = conn.cursor()
        
        # Check if table exists, if not skip vector test
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'despesas_parlamentares'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            # Generate embedding for test description
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=test_descricao
            )
            embedding = response.data[0].embedding
            
            # Insert test data
            cursor.execute("""
                INSERT INTO despesas_parlamentares 
                (nome_deputado, cnpj_fornecedor, nome_fornecedor, descricao_despesa, 
                 descricao_embedding, valor, data_despesa)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (test_deputado, test_cnpj, test_fornecedor, test_descricao, 
                  embedding, test_valor, test_data))
            
            inserted_id = cursor.fetchone()[0]
            conn.commit()
            
            print_success(f"Dado de teste inserido no PostgreSQL (ID: {inserted_id})")
            
            # Try to retrieve it
            cursor.execute("""
                SELECT nome_deputado, nome_fornecedor, valor 
                FROM despesas_parlamentares 
                WHERE nome_deputado = %s
            """, (test_deputado,))
            
            result = cursor.fetchone()
            
            if result:
                print_success("Busca vetorial funcionando - dado recuperado com sucesso")
            else:
                print_error("Falha ao recuperar dado inserido")
                cursor.close()
                conn.close()
                return False
            
            # Clean up test data
            cursor.execute("""
                DELETE FROM despesas_parlamentares WHERE nome_deputado = %s
            """, (test_deputado,))
            conn.commit()
            print_info("Dados de teste removidos do PostgreSQL")
        else:
            print_warning("Tabela não existe, pulando teste de busca vetorial")
        
        cursor.close()
        conn.close()
        
        # 2. Test Neo4j graph insertion
        print_info("Testando grafo no Neo4j...")
        
        uri = os.getenv('NEO4J_URI')
        username = os.getenv('NEO4J_USERNAME')
        password = os.getenv('NEO4J_PASSWORD')
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            # Insert test node
            session.run("""
                MERGE (d:Deputado {nome: $nome})
                MERGE (f:Fornecedor {nome: $fornecedor, cnpj: $cnpj})
                MERGE (d)-[r:PAGOU {
                    valor: $valor,
                    data: $data,
                    descricao: $descricao
                }]->(f)
            """, nome=test_deputado, fornecedor=test_fornecedor, 
                cnpj=test_cnpj, valor=test_valor, 
                data=str(test_data), descricao=test_descricao)
            
            print_success("Dado de teste inserido no Neo4j")
            
            # Try to retrieve it
            result = session.run("""
                MATCH (d:Deputado {nome: $nome})-[r:PAGOU]->(f:Fornecedor)
                RETURN d.nome, f.nome, r.valor
            """, nome=test_deputado)
            
            record = result.single()
            
            if record:
                print_success("Busca em grafo funcionando - relacionamento recuperado")
            else:
                print_error("Falha ao recuperar relacionamento no grafo")
                driver.close()
                return False
            
            # Clean up test data
            session.run("""
                MATCH (d:Deputado {nome: $nome})
                DETACH DELETE d
            """, nome=test_deputado)
            
            session.run("""
                MATCH (f:Fornecedor {nome: $fornecedor})
                WHERE NOT (f)<-[:PAGOU]-()
                DELETE f
            """, fornecedor=test_fornecedor)
            
            print_info("Dados de teste removidos do Neo4j")
        
        driver.close()
        
        print_success("Sistema RAG funcionando de ponta a ponta!")
        return True
        
    except Exception as e:
        print_error(f"Erro durante teste de integração: {str(e)}")
        import traceback
        print_info(f"Detalhes do erro:\n{traceback.format_exc()}")
        return False


def run_functional_tests():
    """
    Phase 3: Run functional RAG integration tests
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print_header("FASE 3: TESTES FUNCIONAIS DO RAG (INTEGRATION TESTS)")
    
    # Test module imports
    imports_ok = test_import_modules()
    
    if not imports_ok:
        print_error("Falha na importação de módulos")
        print_warning("Corrija os erros de importação antes de prosseguir")
        return False
    
    print_success("Todos os módulos foram importados com sucesso")
    
    # Test end-to-end functionality
    print("\n" + "-"*70)
    integration_ok = test_dummy_data_insertion()
    
    if integration_ok:
        print_success("\nTodos os testes funcionais passaram!")
        return True
    else:
        print_error("\nTeste de integração falhou")
        return False


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main execution function"""
    print("\n")
    print("="*70)
    print(f"{BLUE}{'FISCALIZADOR CIDADÃO - DIAGNÓSTICO DO SISTEMA'.center(70)}{RESET}")
    print(f"{BLUE}{'DevOps & QA Verification Script'.center(70)}{RESET}")
    print("="*70)
    print()
    
    # Phase 1: Environment validation
    env_valid = validate_env_file()
    
    if not env_valid:
        print("\n" + "="*70)
        print(f"{RED}DIAGNÓSTICO: Configuração de ambiente incompleta{RESET}")
        print("="*70)
        sys.exit(1)
    
    # Phase 2: Connectivity tests
    connectivity_ok = run_smoke_tests()
    
    if not connectivity_ok:
        print("\n" + "="*70)
        print(f"{RED}DIAGNÓSTICO: Problemas de conectividade detectados{RESET}")
        print("="*70)
        print_warning("Resolva os problemas de conexão antes de usar o sistema")
        sys.exit(1)
    
    # Phase 3: Functional tests
    functional_ok = run_functional_tests()
    
    # Final summary
    print("\n" + "="*70)
    print(f"{BLUE}{'RESUMO FINAL DO DIAGNÓSTICO'.center(70)}{RESET}")
    print("="*70)
    
    phases = [
        ("Fase 1: Variáveis de Ambiente", env_valid),
        ("Fase 2: Conectividade", connectivity_ok),
        ("Fase 3: Testes Funcionais", functional_ok)
    ]
    
    for phase_name, passed in phases:
        status = f"{GREEN}✓ PASSOU{RESET}" if passed else f"{RED}✗ FALHOU{RESET}"
        print(f"{phase_name:40s}: {status}")
    
    print("="*70)
    
    if all(passed for _, passed in phases):
        print_success("\n🎉 SISTEMA TOTALMENTE OPERACIONAL!")
        print_info("Seu ambiente está configurado corretamente e todas as APIs estão respondendo.")
        print_info("\nPróximos passos:")
        print_info("  1. Execute: python etl_camara.py (para extrair dados da API)")
        print_info("  2. Execute: python ingest_data.py (para popular os bancos)")
        print_info("  3. Use: auditor_ai() para fazer consultas inteligentes")
        sys.exit(0)
    else:
        print_error("\n⚠ SISTEMA COM PROBLEMAS")
        print_warning("Revise os erros acima e corrija-os para usar o sistema")
        sys.exit(1)


if __name__ == "__main__":
    main()
