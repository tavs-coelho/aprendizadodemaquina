"""
ETL Script para Dados Abertos da Câmara dos Deputados
======================================================

Este módulo implementa um pipeline ETL (Extract, Transform, Load) robusto
para coletar dados de despesas parlamentares da API oficial da Câmara dos
Deputados do Brasil.

Funcionalidades:
---------------
- Extração automatizada de dados via API REST
- Tratamento de erros com retry logic
- Rate limiting para respeitar limites da API
- Transformação e limpeza de dados
- Exportação para CSV para posterior ingestão

API Utilizada:
-------------
- Base URL: https://dadosabertos.camara.leg.br/api/v2
- Endpoints:
  * /deputados: Lista de deputados ativos
  * /deputados/{id}/despesas: Despesas de um deputado específico

Formato de Saída:
----------------
O script gera um arquivo CSV (despesas_camara.csv) com as seguintes colunas:
- nome: Nome completo do deputado
- siglaPartido: Sigla do partido político
- siglaUf: Unidade Federativa (estado)
- txtDescricao: Descrição/tipo da despesa
- vlrLiquido: Valor líquido da despesa (em reais)
- txtFornecedor: Nome do fornecedor
- cnpjCpfFornecedor: CNPJ ou CPF do fornecedor
- datEmissao: Data de emissão do documento

Autor: Tavs Coelho - Universidade Federal de Goiás (UFG)
Curso: Aprendizado de Máquina
"""

import requests
import csv
import time
from typing import List, Dict, Optional
from datetime import datetime


# Configuração para rate limiting e retentativas
# Estes valores foram calibrados para respeitar os limites da API da Câmara
MAX_RETRIES = 3  # Número máximo de tentativas por requisição
RETRY_DELAY = 2  # Segundos entre retentativas
REQUEST_DELAY = 0.5  # Segundos entre requisições (previne rate limiting)


def fetch_deputies(limit: int = 50) -> List[Dict]:
    """
    Busca lista de deputados da API da Câmara dos Deputados.
    
    Esta função implementa retry logic robusto para lidar com falhas de rede
    e timeouts. As requisições são feitas de forma resiliente, com múltiplas
    tentativas em caso de falha.
    
    Args:
        limit (int): Número máximo de deputados a buscar (padrão: 50)
            Nota: A API retorna deputados paginados. Este valor define o
            tamanho da página (máximo recomendado: 100)
    
    Returns:
        List[Dict]: Lista de dicionários, cada um contendo:
            - id: ID único do deputado
            - nome: Nome completo
            - siglaPartido: Sigla do partido (ex: 'PT', 'PSDB')
            - siglaUf: Estado (ex: 'SP', 'RJ', 'GO')
            - email: Email de contato
            - urlFoto: URL da foto oficial
            
        Retorna lista vazia se todas as tentativas falharem.
    
    Tratamento de Erros:
        - requests.exceptions.Timeout: Timeout na conexão (10 segundos)
        - requests.exceptions.ConnectionError: Erro de conexão com o servidor
        - requests.exceptions.RequestException: Outros erros HTTP
        
        Cada erro resulta em retry automático até MAX_RETRIES tentativas.
    
    Exemplo:
        >>> deputados = fetch_deputies(limit=10)
        >>> print(f"Total de deputados: {len(deputados)}")
        >>> print(f"Primeiro deputado: {deputados[0]['nome']}")
    """
    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    params = {"itens": limit, "ordem": "ASC", "ordenarPor": "nome"}
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Fetching up to {limit} deputies... (Attempt {attempt + 1}/{MAX_RETRIES})")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            deputies = data.get("dados", [])
            print(f"Successfully fetched {len(deputies)} deputies.")
            return deputies
        except requests.exceptions.Timeout as e:
            print(f"Timeout error on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Max retries reached. Failed to fetch deputies.")
                return []
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Max retries reached. Failed to fetch deputies.")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching deputies on attempt {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("Max retries reached. Failed to fetch deputies.")
                return []
    
    return []


def fetch_deputy_expenses(deputy_id, year=None):
    """
    Fetch expenses for a specific deputy for a given year.
    
    Args:
        deputy_id: The ID of the deputy
        year: Year to fetch expenses for (default: current year)
    
    Returns:
        List of expense dictionaries
    """
    if year is None:
        year = datetime.now().year
    
    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputy_id}/despesas"
    params = {"ano": year, "ordem": "ASC", "ordenarPor": "ano"}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            expenses = data.get("dados", [])
            return expenses
        except requests.exceptions.Timeout as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"Error fetching expenses for deputy {deputy_id} after {MAX_RETRIES} attempts: Timeout")
                return []
        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"Error fetching expenses for deputy {deputy_id} after {MAX_RETRIES} attempts: Connection error")
                return []
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                print(f"Error fetching expenses for deputy {deputy_id}: {e}")
                return []
    
    return []


def extract_expense_fields(expense, deputy_info):
    """
    Extract and filter relevant fields from expense data.
    
    Args:
        expense: Expense dictionary from API
        deputy_info: Deputy information dictionary
    
    Returns:
        Dictionary with filtered fields
    """
    return {
        "nome": deputy_info.get("nome", ""),
        "siglaPartido": deputy_info.get("siglaPartido", ""),
        "siglaUf": deputy_info.get("siglaUf", ""),
        "txtDescricao": expense.get("tipoDespesa", ""),
        "vlrLiquido": expense.get("valorLiquido", 0),
        "txtFornecedor": expense.get("nomeFornecedor", ""),
        "cnpjCpfFornecedor": expense.get("cnpjCpfFornecedor", ""),
        "datEmissao": expense.get("dataDocumento", "")
    }


def save_to_csv(data, filename="despesas_camara.csv"):
    """
    Save consolidated expense data to a CSV file.
    
    Args:
        data: List of expense dictionaries
        filename: Output CSV filename (default: despesas_camara.csv)
    """
    if not data:
        print("No data to save.")
        return
    
    fieldnames = [
        "nome", "siglaPartido", "siglaUf", "txtDescricao", 
        "vlrLiquido", "txtFornecedor", "cnpjCpfFornecedor", "datEmissao"
    ]
    
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Successfully saved {len(data)} expense records to {filename}")
    except IOError as e:
        print(f"Error saving to CSV: {e}")


def main():
    """
    Main ETL pipeline execution.
    """
    print("=" * 60)
    print("ETL Pipeline - Chamber of Deputies Expense Data")
    print("=" * 60)
    
    # Step 1: Fetch deputies
    deputies = fetch_deputies(limit=50)
    
    if not deputies:
        print("No deputies found. Exiting.")
        return
    
    # Step 2: Fetch expenses for each deputy
    all_expenses = []
    current_year = datetime.now().year
    
    print(f"\nFetching expenses for year {current_year}...")
    
    for idx, deputy in enumerate(deputies, 1):
        deputy_id = deputy.get("id")
        deputy_name = deputy.get("nome", "Unknown")
        
        print(f"[{idx}/{len(deputies)}] Processing {deputy_name} (ID: {deputy_id})...")
        
        # Fetch expenses for this deputy
        expenses = fetch_deputy_expenses(deputy_id, year=current_year)
        
        # Step 3: Filter and extract relevant fields
        for expense in expenses:
            filtered_expense = extract_expense_fields(expense, deputy)
            all_expenses.append(filtered_expense)
        
        print(f"  Found {len(expenses)} expenses for {deputy_name}")
        
        # Step 4: Add delay between requests to avoid API rate limiting
        # Using constant to make it configurable
        time.sleep(REQUEST_DELAY)
    
    # Step 5: Save consolidated data to CSV
    print(f"\nTotal expenses collected: {len(all_expenses)}")
    save_to_csv(all_expenses)
    
    print("\n" + "=" * 60)
    print("ETL Pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
