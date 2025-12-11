# Exemplos Detalhados de Uso - Fiscalizador Cidadão

Este documento fornece exemplos completos e realistas de como usar o sistema Fiscalizador Cidadão, incluindo código e saídas esperadas.

## 📋 Índice

- [Exemplo 1: Busca Semântica Simples](#exemplo-1-busca-semântica-simples)
- [Exemplo 2: Análise de Deputado Específico](#exemplo-2-análise-de-deputado-específico)
- [Exemplo 3: Análise de Rede de Fornecedores](#exemplo-3-análise-de-rede-de-fornecedores)
- [Exemplo 4: Detecção de Anomalias por Valor](#exemplo-4-detecção-de-anomalias-por-valor)
- [Exemplo 5: Uso Programático em Lote](#exemplo-5-uso-programático-em-lote)

---

## Exemplo 1: Busca Semântica Simples

### Descrição
Busca despesas relacionadas a alimentação usando apenas busca semântica. O sistema entende sinônimos e variações linguísticas.

### Código

```python
from auditor_ai import auditor_ai

resposta = auditor_ai("Mostre gastos suspeitos com alimentação")
print(resposta)
```

### Saída Esperada

```
Com base nos dados recuperados, identifiquei as seguintes despesas com alimentação 
que merecem atenção:

⚠️ DESPESAS DE DESTAQUE:

1. Deputado: João Silva (PT-SP)
   - Fornecedor: Restaurante XYZ Ltda
   - CNPJ: 12.345.678/0001-90
   - Valor: R$ 15.000,00
   - Data: 15/03/2024
   - Observação: Valor significativamente acima da média para fornecimento de 
     alimentação (média típica: R$ 3.000). Concentração de pagamentos ao mesmo 
     fornecedor (5 transações no mesmo mês).

2. Deputado: Maria Santos (PSDB-RJ)
   - Fornecedor: Catering ABC Eventos
   - CNPJ: 98.765.432/0001-10
   - Valor: R$ 8.500,00
   - Data: 20/02/2024
   - Observação: Descrição genérica "Serviços de alimentação" com valor elevado.

3. Deputado: Pedro Costa (MDB-GO)
   - Fornecedor: Buffet Elite
   - CNPJ: 11.222.333/0001-44
   - Valor: R$ 12.300,00
   - Data: 10/01/2024

📊 ANÁLISE AGREGADA:
- Total das despesas apresentadas: R$ 35.800,00
- Valor médio por transação: R$ 11.933,33
- Fornecedores únicos: 3
- Período: Janeiro a Março de 2024

⚠️ PONTOS DE ATENÇÃO:
- Concentração de gastos altos em curto período
- Descrições genéricas em valores acima de R$ 8.000
- Recomenda-se verificação de notas fiscais e justificativas
```

### Explicação Técnica

- **Busca semântica**: O termo "alimentação" encontra semanticamente termos como "restaurante", "catering", "buffet", etc.
- **Embedding**: A descrição é convertida em vetor de 1536 dimensões
- **Similaridade**: O sistema calcula distância de cosseno entre embeddings
- **LLM**: GPT-4o-mini analisa os dados e identifica padrões suspeitos

---

## Exemplo 2: Análise de Deputado Específico

### Descrição
Combina busca lexical (por nome exato) com busca semântica para análise completa de um deputado.

### Código

```python
from auditor_ai import auditor_ai

resposta = auditor_ai(
    "Quanto o deputado João Silva gastou com passagens aéreas em 2024?",
    search_strategies={
        'lexical_deputado': 'João Silva',
        'semantic': True
    }
)
print(resposta)
```

### Saída Esperada

```
Análise de Despesas - Deputado João Silva

📝 RESUMO:
Deputado: João Silva
Partido: PT
Estado: São Paulo (SP)
Período analisado: Janeiro a Dezembro de 2024
Categoria: Passagens Aéreas

💰 VALORES:
- Número de transações: 24 passagens
- Valor total: R$ 89.450,00
- Valor médio por passagem: R$ 3.727,08
- Valor mínimo: R$ 850,00 (voo regional)
- Valor máximo: R$ 8.900,00 (voo internacional)

📍 DESTINOS PRINCIPAIS:
1. Brasília-São Paulo: 12 viagens (R$ 32.400,00)
2. Brasília-Rio de Janeiro: 5 viagens (R$ 18.750,00)
3. Brasília-Goiânia: 4 viagens (R$ 12.800,00)
4. Internacional (Miami): 1 viagem (R$ 8.900,00)
5. Outros: 2 viagens (R$ 16.600,00)

🔍 OBSERVAÇÕES:
- Frequência compatível com atividade parlamentar esperada
- Valor internacional requer análise: viagem a Miami por R$ 8.900 em Julho/2024
  pode necessitar justificativa de evento oficial
- Demais valores dentro da faixa normal de mercado

📊 COMPARAÇÃO:
- Média de gastos de deputados de SP com passagens: R$ 72.000/ano
- João Silva: R$ 89.450 (23,4% acima da média estadual)
```

### Explicação Técnica

- **Busca lexical**: SQL LIKE query no PostgreSQL filtra por nome exato
- **Busca semântica**: Encontra descrições relacionadas a "passagens aéreas"
- **RRF**: Combina ambos os resultados, priorizando itens que aparecem em ambas as buscas
- **Análise**: LLM compara com médias e identifica outliers

---

## Exemplo 3: Análise de Rede de Fornecedores

### Descrição
Usa busca em grafo (Neo4j) para identificar todos os deputados que contrataram o mesmo fornecedor.

### Código

```python
from auditor_ai import auditor_ai

resposta = auditor_ai(
    "Quais deputados fizeram pagamentos para a empresa com CNPJ 12345678000190?",
    search_strategies={
        'lexical_cnpj': '12345678000190',
        'graph_patterns': {
            'type': 'fornecedor_deputados',
            'value': '12345678000190'
        },
        'semantic': True
    }
)
print(resposta)
```

### Saída Esperada

```
Análise de Rede de Fornecedor

🏢 FORNECEDOR:
Nome: Consultoria ABC Ltda
CNPJ: 12.345.678/0001-90
Atividade: Serviços de consultoria e assessoria

👥 DEPUTADOS CONTRATANTES (7 deputados encontrados):

1. Deputado: João Silva (PT-SP)
   - Transações: 8
   - Total pago: R$ 145.000,00
   - Período: Jan-Ago 2024
   - Média por transação: R$ 18.125,00

2. Deputado: Maria Santos (PSDB-RJ)
   - Transações: 5
   - Total pago: R$ 87.500,00
   - Período: Mar-Jul 2024
   - Média por transação: R$ 17.500,00

3. Deputado: Pedro Costa (MDB-GO)
   - Transações: 6
   - Total pago: R$ 102.000,00
   - Período: Fev-Jun 2024
   - Média por transação: R$ 17.000,00

[... mais 4 deputados ...]

📊 ESTATÍSTICAS AGREGADAS:
- Total de deputados: 7
- Total pago por todos: R$ 523.500,00
- Média por deputado: R$ 74.785,71
- Total de transações: 34
- Média por transação: R$ 15.397,06

🚨 ALERTAS DE AUDITORIA:

⚠️ ALTA CONCENTRAÇÃO:
Esta empresa recebe pagamentos de 7 deputados diferentes, sugerindo possível 
especialização ou rede estabelecida de relacionamentos políticos.

⚠️ VALORES UNIFORMES:
Valores médios muito similares (R$ 17.000-18.000) entre diferentes deputados 
podem indicar contratos padronizados ou preços tabelados.

⚠️ PERÍODO CONCENTRADO:
Maioria das contratações ocorreram entre Fevereiro e Agosto de 2024 (6 meses),
coincidindo com período pré-eleitoral.

⚠️ DESCRIÇÕES GENÉRICAS:
Análise das descrições mostra uso frequente de termos vagos como "consultoria", 
"assessoria" e "serviços especializados" sem especificação de entregas.

📋 RECOMENDAÇÕES:
1. Solicitar relatórios detalhados de serviços prestados
2. Verificar contratos e termos de referência
3. Confirmar expertise da empresa na área
4. Avaliar se há conflito de interesse entre múltiplas contratações simultâneas
5. Comparar valores com mercado para serviços similares
```

### Explicação Técnica

- **Busca em grafo**: Query Cypher no Neo4j: `MATCH (f:Fornecedor {cnpj: X})<-[:PAGOU]-(d:Deputado)`
- **Agregação**: Neo4j COUNT e SUM para calcular estatísticas
- **Pattern matching**: Identifica redes de relacionamento
- **Análise crítica**: LLM identifica concentração e padrões suspeitos

---

## Exemplo 4: Detecção de Anomalias por Valor

### Descrição
Busca despesas outliers acima de um threshold usando busca em grafo.

### Código

```python
from auditor_ai import auditor_ai

resposta = auditor_ai(
    "Mostre despesas acima de R$ 50.000,00",
    search_strategies={
        'graph_patterns': {
            'type': 'valor_alto',
            'value': 50000
        },
        'semantic': True
    }
)
print(resposta)
```

### Saída Esperada

```
Relatório de Despesas de Alto Valor (> R$ 50.000)

🔎 ANÁLISE DE OUTLIERS

Total de despesas encontradas: 5
Valor total: R$ 387.600,00
Valor médio: R$ 77.520,00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 DESPESA #1 - MAIOR VALOR ENCONTRADO
Deputado: Carlos Eduardo (PP-BA)
Fornecedor: Empresa de Consultoria Premium Ltda
CNPJ: 55.444.333/0001-22
Descrição: Consultoria estratégica especializada
Valor: R$ 98.500,00 🚨
Data: 15/06/2024

⚠️ Observações Críticas:
- Maior valor individual identificado no período
- Descrição genérica para valor extremamente alto
- Não há detalhamento do escopo da consultoria
- Valor representa 32% do limite mensal da CEAP
- Requer justificativa técnica detalhada

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 DESPESA #2
Deputado: Ana Paula (PSOL-RJ)
Fornecedor: Agência de Publicidade XYZ
CNPJ: 88.777.666/0001-99
Descrição: Campanha de divulgação institucional
Valor: R$ 85.300,00
Data: 22/04/2024

⚠️ Observações:
- Gastos com divulgação representam uso permitido da CEAP
- Valor está no limite superior aceitável
- Período não eleitoral (antes das convenções)
- Recomenda-se verificar materiais produzidos

[... demais despesas ...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 ANÁLISE COMPARATIVA:

Distribuição por Tipo:
- Consultoria: R$ 183.500 (47.3%) - 2 despesas
- Publicidade: R$ 85.300 (22.0%) - 1 despesa
- Locação: R$ 68.000 (17.5%) - 1 despesa
- Eventos: R$ 50.800 (13.1%) - 1 despesa

Estados com Maior Concentração:
1. Bahia: R$ 98.500
2. Rio de Janeiro: R$ 153.300
3. São Paulo: R$ 135.800

🔴 BANDEIRAS VERMELHAS IDENTIFICADAS:

1. Três deputados (60%) usaram o termo genérico "consultoria" para despesas 
   acima de R$ 50.000
2. Média de valor (R$ 77.520) é 4.5x maior que a média nacional (R$ 17.200)
3. Concentração temporal: 4 das 5 despesas ocorreram entre Abril-Junho
4. Dois fornecedores recebem de múltiplos deputados

🎯 RECOMENDAÇÕES PARA FISCALIZAÇÃO:

1. URGENTE: Solicitar relatórios técnicos das consultorias (Despesa #1 e #3)
2. ALTA: Verificar conformidade das campanhas de divulgação com normas
3. MÉDIA: Auditar contratos de locação de valores elevados
4. PREVENTIVA: Estabelecer tetos por categoria de despesa

Todas as despesas listadas devem ser objeto de análise detalhada pelos órgãos 
de controle, dado o valor expressivo e potencial impacto nos recursos públicos.
```

### Explicação Técnica

- **Busca em grafo**: Query com filtro de valor: `WHERE r.valor >= $threshold`
- **Ordenação**: ORDER BY valor DESC para priorizar maiores valores
- **Estatísticas**: Agregação de totais, médias e distribuições
- **Comparação**: LLM compara com médias nacionais e identifica outliers

---

## Exemplo 5: Uso Programático em Lote

### Descrição
Exemplo de como usar o sistema programaticamente para analisar múltiplos deputados em batch.

### Código

```python
from auditor_ai import auditor_ai
import pandas as pd
from datetime import datetime

# Lista de deputados para análise
deputados = ["João Silva", "Maria Santos", "Pedro Costa"]
resultados = []

print("="*60)
print("RELATÓRIO DE AUDITORIA EM LOTE")
print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print(f"Deputados analisados: {len(deputados)}")
print("="*60)

for i, deputado in enumerate(deputados, 1):
    print(f"\n[{i}/{len(deputados)}] Analisando {deputado}...")
    
    try:
        resposta = auditor_ai(
            f"Resuma os gastos do deputado {deputado} em 2024",
            search_strategies={
                'lexical_deputado': deputado,
                'semantic': True
            }
        )
        
        resultados.append({
            'deputado': deputado,
            'status': 'Sucesso',
            'analise': resposta,
            'timestamp': datetime.now()
        })
        print(f"   ✓ Análise concluída para {deputado}")
        
    except Exception as e:
        print(f"   ✗ Erro ao analisar {deputado}: {e}")
        resultados.append({
            'deputado': deputado,
            'status': 'Erro',
            'analise': str(e),
            'timestamp': datetime.now()
        })

# Salvar relatório consolidado
df = pd.DataFrame(resultados)
filename = f'relatorio_auditoria_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
df.to_csv(filename, index=False, encoding='utf-8-sig')

print("\n" + "="*60)
print(f"✅ Análise de {len(deputados)} deputados concluída!")
print(f"📄 Relatório salvo em: {filename}")
print(f"   Sucessos: {len([r for r in resultados if r['status'] == 'Sucesso'])}")
print(f"   Erros: {len([r for r in resultados if r['status'] == 'Erro'])}")
print("="*60)
```

### Saída Esperada

```
============================================================
RELATÓRIO DE AUDITORIA EM LOTE
Data: 10/12/2024 15:30
Deputados analisados: 3
============================================================

[1/3] Analisando João Silva...
   ✓ Análise concluída para João Silva

[2/3] Analisando Maria Santos...
   ✓ Análise concluída para Maria Santos

[3/3] Analisando Pedro Costa...
   ✓ Análise concluída para Pedro Costa

============================================================
✅ Análise de 3 deputados concluída!
📄 Relatório salvo em: relatorio_auditoria_20241210_1530.csv
   Sucessos: 3
   Erros: 0
============================================================
```

### Arquivo CSV Gerado

| deputado      | status  | analise                                    | timestamp           |
|---------------|---------|-------------------------------------------|---------------------|
| João Silva    | Sucesso | Análise completa dos gastos de João...    | 2024-12-10 15:30:15 |
| Maria Santos  | Sucesso | Análise completa dos gastos de Maria...   | 2024-12-10 15:30:32 |
| Pedro Costa   | Sucesso | Análise completa dos gastos de Pedro...   | 2024-12-10 15:30:47 |

### Casos de Uso para Análise em Lote

1. **Auditoria Periódica**: Analisar todos os deputados de um estado mensalmente
2. **Monitoramento de Partidos**: Comparar gastos entre deputados do mesmo partido
3. **Alertas Automatizados**: Detectar padrões suspeitos em tempo real
4. **Relatórios Consolidados**: Gerar dashboards com análises agregadas

---

## 🔧 Dicas de Uso Avançado

### Customizando Análises

```python
# Busca combinada: lexical + semântica + grafo
resposta = auditor_ai(
    "Análise completa de gastos suspeitos",
    search_strategies={
        'lexical_deputado': 'João Silva',
        'lexical_cnpj': '12345678000190',
        'semantic': True,
        'graph_patterns': {
            'type': 'deputado_fornecedores',
            'value': 'João Silva'
        }
    }
)
```

### Tratamento de Erros

```python
from auditor_ai import auditor_ai
import logging

logging.basicConfig(level=logging.INFO)

try:
    resposta = auditor_ai("Sua pergunta aqui")
    print(resposta)
except ValueError as e:
    print(f"Erro de configuração: {e}")
    print("Verifique suas variáveis de ambiente (.env)")
except Exception as e:
    print(f"Erro inesperado: {e}")
    logging.exception("Detalhes do erro:")
```

### Otimizando Performance

```python
# Cache de resultados frequentes
import functools

@functools.lru_cache(maxsize=100)
def buscar_deputado_cached(nome):
    return auditor_ai(
        f"Gastos do deputado {nome}",
        search_strategies={'lexical_deputado': nome}
    )

# Usar o cache
resposta1 = buscar_deputado_cached("João Silva")  # Primeira chamada: lenta
resposta2 = buscar_deputado_cached("João Silva")  # Segunda chamada: instantânea (cache)
```

---

## 📚 Recursos Adicionais

- [README Principal](README.md)
- [Guia de Contribuição](CONTRIBUTING.md)
- [Documentação da API da Câmara](https://dadosabertos.camara.leg.br/swagger/api.html)
- [Documentação OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Neo4j Cypher Reference](https://neo4j.com/docs/cypher-manual/current/)

---

**Desenvolvido com ❤️ para transparência pública**  
**Universidade Federal de Goiás (UFG) - 2024**
