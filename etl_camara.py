"""
ETL Script for Chamber of Deputies Open Data API
Extracts, transforms, and loads deputy expense data from Brazilian Chamber of Deputies.
"""

import requests
import csv
import time
from datetime import datetime


# Configuration for API rate limiting and retries
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_DELAY = 0.5  # seconds between requests to avoid rate limiting


def fetch_deputies(limit=50):
    """
    Fetch list of deputies from the Chamber of Deputies API.
    
    Args:
        limit: Maximum number of deputies to fetch (default: 50)
    
    Returns:
        List of deputy dictionaries with their information
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
