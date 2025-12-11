"""
Script de Preparação de Artefatos de Dados
===========================================

Este script automatiza a criação de evidências sobre os dados extraídos
pela API da Câmara dos Deputados, preparando artefatos para commit no Git.

Funcionalidades:
---------------
1. Executa e valida o ETL (etl_camara.py) se necessário
2. Gera amostra dos top 50 registros mais relevantes
3. Cria relatório de qualidade de dados (DATA_DICTIONARY.md)
4. Fornece comandos Git para commit dos artefatos

Autor: Tavs Coelho - Fiscalizador Cidadão
Data: 2025
"""

import os
import sys
import subprocess
import pandas as pd
from datetime import datetime
from pathlib import Path


def check_and_run_etl():
    """
    Verifica se o arquivo despesas_camara.csv existe.
    Se não existir, executa o módulo etl_camara.py para baixá-lo.
    """
    csv_file = "despesas_camara.csv"
    
    if os.path.exists(csv_file):
        print(f"✓ Arquivo {csv_file} encontrado.")
        return True
    
    print(f"✗ Arquivo {csv_file} não encontrado.")
    print("Executando etl_camara.py para baixar os dados...")
    
    try:
        # Executa o script ETL
        result = subprocess.run(
            [sys.executable, "etl_camara.py"],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutos de timeout
        )
        
        if result.returncode == 0:
            print("✓ ETL executado com sucesso!")
            if os.path.exists(csv_file):
                return True
            else:
                print(f"✗ Erro: ETL executado mas {csv_file} não foi criado.")
                return False
        else:
            print(f"✗ Erro ao executar ETL:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Erro: ETL excedeu o tempo limite de 10 minutos.")
        return False
    except Exception as e:
        print(f"✗ Erro ao executar ETL: {e}")
        return False


def load_and_validate_data(csv_file="despesas_camara.csv"):
    """
    Carrega o CSV completo e valida os dados.
    
    Returns:
        tuple: (DataFrame, estatísticas) ou (None, None) em caso de erro
    """
    try:
        print(f"\nCarregando {csv_file}...")
        df = pd.read_csv(csv_file)
        
        # Validação básica
        if df.empty:
            print("✗ Erro: Dataset vazio!")
            return None, None
        
        # Calcula estatísticas
        total_rows = len(df)
        
        # Converte vlrLiquido para numérico, tratando erros
        df['vlrLiquido'] = pd.to_numeric(df['vlrLiquido'], errors='coerce')
        total_value = df['vlrLiquido'].sum()
        
        # Converte datas e encontra min/max
        df['datEmissao'] = pd.to_datetime(df['datEmissao'], errors='coerce')
        date_min = df['datEmissao'].min()
        date_max = df['datEmissao'].max()
        
        stats = {
            'total_rows': total_rows,
            'total_value': total_value,
            'date_min': date_min,
            'date_max': date_max
        }
        
        print(f"✓ Dataset carregado com sucesso!")
        print(f"  - Total de registros: {total_rows:,}")
        print(f"  - Valor total: R$ {total_value:,.2f}")
        print(f"  - Período: {date_min.strftime('%Y-%m-%d') if pd.notna(date_min) else 'N/A'} a {date_max.strftime('%Y-%m-%d') if pd.notna(date_max) else 'N/A'}")
        
        return df, stats
        
    except FileNotFoundError:
        print(f"✗ Erro: Arquivo {csv_file} não encontrado!")
        return None, None
    except Exception as e:
        print(f"✗ Erro ao carregar dados: {e}")
        return None, None


def create_sample_top50(df, output_dir="data"):
    """
    Extrai as top 50 linhas com maiores valores e salva em arquivo separado.
    
    Args:
        df: DataFrame com os dados completos
        output_dir: Diretório de saída (padrão: 'data')
    """
    try:
        # Cria diretório se não existir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Ordena por valor decrescente e pega top 50
        df_sorted = df.sort_values('vlrLiquido', ascending=False)
        df_top50 = df_sorted.head(50)
        
        # Salva em arquivo
        output_file = os.path.join(output_dir, "despesas_sample_top50.csv")
        df_top50.to_csv(output_file, index=False)
        
        print(f"\n✓ Amostra top 50 criada: {output_file}")
        print(f"  - Valor total da amostra: R$ {df_top50['vlrLiquido'].sum():,.2f}")
        
        return output_file
        
    except Exception as e:
        print(f"✗ Erro ao criar amostra: {e}")
        return None


def get_top_suppliers(df, top_n=5):
    """
    Agrega os top N fornecedores por valor total recebido.
    
    Args:
        df: DataFrame com os dados
        top_n: Número de fornecedores a retornar (padrão: 5)
        
    Returns:
        DataFrame com os top fornecedores
    """
    try:
        # Agrupa por fornecedor e soma valores
        suppliers = df.groupby('txtFornecedor')['vlrLiquido'].agg(['sum', 'count']).reset_index()
        suppliers.columns = ['Fornecedor', 'Valor Total (R$)', 'Quantidade de Despesas']
        
        # Ordena por valor total decrescente
        suppliers = suppliers.sort_values('Valor Total (R$)', ascending=False)
        
        return suppliers.head(top_n)
        
    except Exception as e:
        print(f"✗ Erro ao calcular top fornecedores: {e}")
        return pd.DataFrame()


def generate_data_dictionary(df, stats, top_suppliers):
    """
    Gera o arquivo DATA_DICTIONARY.md com informações sobre o dataset.
    
    Args:
        df: DataFrame com os dados
        stats: Dicionário com estatísticas do dataset
        top_suppliers: DataFrame com top fornecedores
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Prepara informações do schema
        schema_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            # Traduz tipos do pandas para tipos mais amigáveis
            if dtype.startswith('int'):
                dtype_friendly = 'Inteiro'
            elif dtype.startswith('float'):
                dtype_friendly = 'Decimal'
            elif dtype.startswith('object'):
                dtype_friendly = 'Texto'
            elif dtype.startswith('datetime'):
                dtype_friendly = 'Data'
            else:
                dtype_friendly = dtype
            
            schema_info.append((col, dtype_friendly))
        
        # Gera conteúdo do markdown
        content = f"""# Dicionário de Dados - Fiscalizador Cidadão

## 📊 Resumo do Dataset

Dataset extraído em **{today}** contendo **{stats['total_rows']:,}** registros totalizando **R$ {stats['total_value']:,.2f}**.

**Período dos dados:** {stats['date_min'].strftime('%Y-%m-%d') if pd.notna(stats['date_min']) else 'N/A'} a {stats['date_max'].strftime('%Y-%m-%d') if pd.notna(stats['date_max']) else 'N/A'}

---

## 🗂️ Schema do Dataset

| Coluna | Tipo de Dado | Descrição |
|--------|--------------|-----------|
"""
        
        # Adiciona descrições das colunas
        column_descriptions = {
            'nome': 'Nome completo do deputado',
            'siglaPartido': 'Sigla do partido político',
            'siglaUf': 'Unidade Federativa (estado)',
            'txtDescricao': 'Descrição/tipo da despesa',
            'vlrLiquido': 'Valor líquido da despesa (em reais)',
            'txtFornecedor': 'Nome do fornecedor',
            'cnpjCpfFornecedor': 'CNPJ ou CPF do fornecedor',
            'datEmissao': 'Data de emissão do documento'
        }
        
        for col, dtype in schema_info:
            desc = column_descriptions.get(col, 'N/A')
            content += f"| `{col}` | {dtype} | {desc} |\n"
        
        content += "\n---\n\n## 🏆 Top 5 Fornecedores\n\n"
        
        if not top_suppliers.empty:
            content += "| Posição | Fornecedor | Valor Total (R$) | Qtd. Despesas |\n"
            content += "|---------|------------|------------------|---------------|\n"
            
            for pos, (idx, row) in enumerate(top_suppliers.iterrows(), 1):
                content += f"| {pos}º | {row['Fornecedor']} | R$ {row['Valor Total (R$)']:,.2f} | {int(row['Quantidade de Despesas'])} |\n"
        else:
            content += "*Dados não disponíveis*\n"
        
        content += """
---

## 🔄 Instruções de Reprodução

Para gerar o dataset completo novamente, execute:

```bash
python etl_camara.py
```

**Observações:**
- O script faz requisições à API oficial da Câmara dos Deputados
- O processo pode levar alguns minutos dependendo da quantidade de dados
- É necessário conexão com a internet
- O arquivo completo `despesas_camara.csv` não é commitado no Git (apenas a amostra)

---

## 📁 Estrutura de Arquivos

- **`despesas_sample_top50.csv`**: Amostra com os 50 maiores valores (commitado no Git)
- **`despesas_camara.csv`**: Dataset completo (não commitado, regenerado via ETL)
- **`DATA_DICTIONARY.md`**: Este arquivo de documentação

---

## 📝 Metadados

- **Fonte dos Dados**: [API Dados Abertos - Câmara dos Deputados](https://dadosabertos.camara.leg.br/)
- **Última Atualização**: {today}
- **Gerado por**: `prepare_data_artifacts.py`

---

*Este documento foi gerado automaticamente pelo script de preparação de artefatos.*
"""
        
        # Ensure template variables are replaced
        # Note: Manual replacement needed due to Python f-string quirk with unicode characters
        # in multiline strings. The f-string should work but sometimes doesn't interpolate correctly.
        content = content.replace('{today}', today)
        
        # Salva o arquivo
        output_file = "DATA_DICTIONARY.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✓ Dicionário de dados criado: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"✗ Erro ao gerar dicionário de dados: {e}")
        return None


def print_git_commands(sample_file, dict_file):
    """
    Imprime comandos Git sugeridos para o usuário.
    
    Args:
        sample_file: Caminho do arquivo de amostra
        dict_file: Caminho do arquivo de dicionário
    """
    print("\n" + "="*70)
    print("🎉 ARTEFATOS CRIADOS COM SUCESSO!")
    print("="*70)
    
    print("\n📝 Comandos Git sugeridos:\n")
    print(f"  git add {sample_file}")
    print(f"  git add {dict_file}")
    print('  git commit -m "feat: Add data artifacts and documentation"')
    print("  git push")
    
    print("\n⚠️  IMPORTANTE: Verifique se o .gitignore está correto!\n")
    print("  O arquivo 'despesas_camara.csv' deve estar no .gitignore")
    print("  para evitar commitar o dataset completo.")
    
    # Verifica se está no .gitignore
    gitignore_file = ".gitignore"
    if os.path.exists(gitignore_file):
        with open(gitignore_file, 'r') as f:
            gitignore_content = f.read()
            if "despesas_camara.csv" in gitignore_content:
                print("  ✓ despesas_camara.csv já está no .gitignore")
            else:
                print("  ✗ ATENÇÃO: despesas_camara.csv NÃO está no .gitignore!")
                print("  Execute: echo 'despesas_camara.csv' >> .gitignore")
    
    print("\n" + "="*70)


def main():
    """
    Função principal que orquestra todo o processo.
    """
    print("="*70)
    print("🔍 FISCALIZADOR CIDADÃO - Preparação de Artefatos de Dados")
    print("="*70)
    
    # Passo 1: Verificar e executar ETL se necessário
    print("\n[Passo 1/4] Validando arquivo de dados...")
    if not check_and_run_etl():
        print("\n✗ Falha ao obter dados. Abortando.")
        sys.exit(1)
    
    # Passo 2: Carregar e validar dados
    print("\n[Passo 2/4] Carregando e validando dados...")
    df, stats = load_and_validate_data()
    if df is None:
        print("\n✗ Falha ao carregar dados. Abortando.")
        sys.exit(1)
    
    # Passo 3: Gerar amostra top 50
    print("\n[Passo 3/4] Gerando amostra dos top 50 registros...")
    sample_file = create_sample_top50(df)
    if sample_file is None:
        print("\n✗ Falha ao criar amostra. Abortando.")
        sys.exit(1)
    
    # Passo 4: Gerar dicionário de dados
    print("\n[Passo 4/4] Gerando dicionário de dados...")
    top_suppliers = get_top_suppliers(df)
    dict_file = generate_data_dictionary(df, stats, top_suppliers)
    if dict_file is None:
        print("\n✗ Falha ao criar dicionário. Abortando.")
        sys.exit(1)
    
    # Instruções finais
    print_git_commands(sample_file, dict_file)


if __name__ == "__main__":
    main()
