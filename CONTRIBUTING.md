# Guia de Contribuição - Fiscalizador Cidadão

Obrigado pelo interesse em contribuir com o projeto Fiscalizador Cidadão! Este documento fornece diretrizes para colaboradores.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Contribuir](#como-contribuir)
- [Padrões de Código](#padrões-de-código)
- [Processo de Pull Request](#processo-de-pull-request)
- [Reportando Bugs](#reportando-bugs)
- [Sugerindo Melhorias](#sugerindo-melhorias)

---

## 📜 Código de Conduta

Este projeto segue os princípios de:
- **Respeito**: Trate todos os colaboradores com respeito
- **Inclusão**: Acolha contribuições de todos os níveis
- **Colaboração**: Trabalhe em conjunto para melhorar o projeto
- **Transparência**: Mantenha comunicação clara e aberta

---

## 🤝 Como Contribuir

### Áreas de Contribuição

1. **Código**:
   - Correção de bugs
   - Novas funcionalidades
   - Otimizações de performance
   - Testes automatizados

2. **Documentação**:
   - Melhorias no README
   - Tutoriais e guias
   - Comentários no código
   - Exemplos de uso

3. **Dados**:
   - Novos datasets
   - Validação de dados
   - Limpeza de dados

4. **Pesquisa**:
   - Análises estatísticas
   - Benchmarks de performance
   - Artigos e publicações

### Configuração do Ambiente de Desenvolvimento

```bash
# 1. Fork e clone o repositório
git clone https://github.com/seu-usuario/aprendizadodemaquina.git
cd aprendizadodemaquina

# 2. Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# 3. Instale dependências de desenvolvimento
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Se disponível

# 4. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 5. Verifique a instalação
python setup_and_verify.py
```

---

## 💻 Padrões de Código

### Python Style Guide

Seguimos a [PEP 8](https://pep8.org/) com algumas adaptações:

```python
# ✅ BOM: Nomes descritivos e type hints
def calcular_total_despesas(deputado_id: int, ano: int) -> float:
    """
    Calcula o total de despesas de um deputado em um ano.
    
    Args:
        deputado_id: ID único do deputado
        ano: Ano fiscal (ex: 2024)
    
    Returns:
        Total de despesas em reais
    """
    pass

# ❌ RUIM: Nomes vagos sem documentação
def calc(d, y):
    pass
```

### Docstrings

Use o formato Google Style:

```python
def funcao_exemplo(parametro1: str, parametro2: int = 10) -> bool:
    """
    Breve descrição da função em uma linha.
    
    Descrição mais detalhada da função, explicando seu propósito,
    comportamento e casos de uso especiais.
    
    Args:
        parametro1: Descrição do primeiro parâmetro
        parametro2: Descrição do segundo parâmetro (padrão: 10)
    
    Returns:
        Descrição do valor retornado
    
    Raises:
        ValueError: Quando parametro1 está vazio
        TypeError: Quando parametro2 não é inteiro
    
    Example:
        >>> resultado = funcao_exemplo("teste", 20)
        >>> print(resultado)
        True
    """
    pass
```

### Comentários

```python
# ✅ BOM: Comentário explica o "porquê"
# Sanitizamos o CNPJ para evitar duplicatas no Neo4j devido a
# diferentes formatos retornados pela API (com/sem pontuação)
cnpj = sanitize_cnpj(raw_cnpj)

# ❌ RUIM: Comentário apenas repete o código
# Remove pontos do CNPJ
cnpj = raw_cnpj.replace('.', '')
```

### Tratamento de Erros

```python
# ✅ BOM: Erro específico com mensagem clara
if not openai_api_key:
    raise ValueError(
        "OPENAI_API_KEY não configurada. "
        "Por favor, defina esta variável no arquivo .env"
    )

# ❌ RUIM: Erro genérico sem contexto
if not openai_api_key:
    raise Exception("Erro!")
```

---

## 🔄 Processo de Pull Request

### Antes de Abrir um PR

1. **Crie uma branch**:
   ```bash
   git checkout -b feature/minha-funcionalidade
   # ou
   git checkout -b fix/correcao-bug
   ```

2. **Execute os testes**:
   ```bash
   python test_fiscalizador.py
   ```

3. **Verifique o estilo**:
   ```bash
   # Se tiver flake8 instalado
   flake8 *.py
   ```

4. **Atualize a documentação**: Se sua mudança afeta a API ou uso

### Template de Pull Request

```markdown
## Descrição
Breve descrição das mudanças realizadas.

## Tipo de Mudança
- [ ] Bug fix (correção que não quebra funcionalidade existente)
- [ ] Nova funcionalidade (mudança que adiciona funcionalidade)
- [ ] Breaking change (mudança que pode quebrar código existente)
- [ ] Documentação

## Como Testar
Passo a passo para testar suas mudanças:
1. Execute o comando X
2. Verifique que Y acontece
3. Confirme que Z está correto

## Checklist
- [ ] Meu código segue o estilo do projeto
- [ ] Revisei meu próprio código
- [ ] Comentei partes complexas do código
- [ ] Atualizei a documentação
- [ ] Não gerei novos warnings
- [ ] Adicionei testes que provam que a correção/funcionalidade funciona
- [ ] Testes novos e existentes passam localmente
```

### Revisão de Código

Seu PR será revisado quanto a:
- **Funcionalidade**: O código faz o que promete?
- **Qualidade**: O código é limpo e bem estruturado?
- **Testes**: Há testes adequados?
- **Documentação**: As mudanças estão documentadas?
- **Performance**: Há impacto na performance?
- **Segurança**: Há vulnerabilidades introduzidas?

---

## 🐛 Reportando Bugs

### Template de Issue para Bugs

```markdown
**Descrição do Bug**
Descrição clara e concisa do problema.

**Passos para Reproduzir**
1. Vá para '...'
2. Execute '...'
3. Observe o erro '...'

**Comportamento Esperado**
O que deveria acontecer.

**Comportamento Atual**
O que acontece atualmente.

**Screenshots**
Se aplicável, adicione screenshots.

**Ambiente**
- OS: [ex: Ubuntu 22.04]
- Python: [ex: 3.10.5]
- Versão: [ex: commit abc123]

**Logs**
```
Cole logs relevantes aqui
```

**Contexto Adicional**
Qualquer outra informação relevante.
```

---

## 💡 Sugerindo Melhorias

### Template de Issue para Features

```markdown
**Descrição da Feature**
Descrição clara da funcionalidade proposta.

**Problema que Resolve**
Qual problema esta feature resolve?

**Solução Proposta**
Como você imagina que isso deveria funcionar?

**Alternativas Consideradas**
Quais outras soluções você considerou?

**Exemplos de Uso**
```python
# Exemplo de como a feature seria usada
resultado = nova_funcao(parametros)
```

**Impacto**
- Performance: [alto/médio/baixo]
- Complexidade: [alta/média/baixa]
- Prioridade: [alta/média/baixa]
```

---

## 🧪 Testes

### Escrevendo Testes

```python
def test_sanitize_cnpj():
    """Testa sanitização de CNPJ com diferentes formatos"""
    # Arrange
    cnpj_formatado = "12.345.678/0001-90"
    expected = "12345678000190"
    
    # Act
    result = sanitize_cnpj(cnpj_formatado)
    
    # Assert
    assert result == expected, f"Esperado {expected}, obtido {result}"
```

### Executando Testes

```bash
# Executar todos os testes
python test_fiscalizador.py

# Com coverage (se disponível)
pytest --cov=. --cov-report=html
```

---

## 📚 Recursos Adicionais

- [Python PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

## 🙏 Reconhecimentos

Agradecemos a todos os colaboradores que ajudam a melhorar este projeto!

### Como seu Nome Aparecerá

Contribuidores são automaticamente reconhecidos:
- Na página de contributors do GitHub
- No arquivo AUTHORS (se mantido)
- Nos release notes para contribuições significativas

---

## 📧 Contato

- **Issues**: Use o [GitHub Issues](https://github.com/tavs-coelho/aprendizadodemaquina/issues)
- **Discussões**: Use [GitHub Discussions](https://github.com/tavs-coelho/aprendizadodemaquina/discussions)
- **Email**: Para questões privadas, contate via UFG

---

**Obrigado por contribuir! 🎉**
