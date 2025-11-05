# Dashboard Mercado Livre Ads — PyScript

Dashboard interativo para análise de dados de anúncios patrocinados do Mercado Livre, processado completamente no navegador usando PyScript.

## Estrutura do Projeto

- **`index.html`** - Interface HTML com visualizações (Plotly), tabelas (DataTables) e lógica JavaScript
- **`main.py`** - Processamento de dados em Python usando pandas (executa no navegador via PyScript/Pyodide)

## Funcionalidades

- 📊 **Processamento client-side**: Todo o processamento acontece no navegador, sem necessidade de servidor
- 📈 **Visualizações interativas**: Gráficos de desempenho diário, tendências de ROAS/ACOS/CPC
- 📋 **Tabela de dados**: Visualização e filtragem dos dados processados
- 💾 **Export CSV**: Exportação dos dados processados
- 🎯 **KPIs**: Investimento total, receita, ROAS médio, ACOS médio, CPC médio

## Pré-requisitos

- **Python 3.7+** instalado no sistema (https://www.python.org/downloads/)
- **Navegador moderno** com suporte a WebAssembly (Chrome, Firefox, Edge)
- **Conexão com internet** (para carregar bibliotecas CDN na primeira execução)

## Instalação

1. Clone ou baixe os arquivos do projeto:
   ```bash
   git clone <repository-url>
   cd <project-folder>
   ```

2. Verifique a instalação do Python:
   ```bash
   python3 --version
   ```

3. Não são necessárias dependências adicionais - todas as bibliotecas são carregadas via CDN

## Como Usar

1. Inicie um servidor HTTP local no diretório do projeto:
   ```bash
   python3 -m http.server 8000
   ```
2. Abra o navegador e acesse `http://localhost:8000`
3. Aguarde o carregamento do PyScript (alguns segundos na primeira vez)
4. Selecione o arquivo Excel com a aba **"Relatório Anúncios patrocinados"**
5. Clique em **"Processar arquivo"**
6. Visualize os KPIs, gráficos e tabela de dados

## Tecnologias

- **PyScript 2025.10.3** - Python no navegador
- **Pandas** - Processamento e análise de dados
- **Plotly** - Visualizações interativas
- **DataTables** - Tabelas interativas
- **Bootstrap 5** - Interface responsiva
- **SheetJS (XLSX)** - Leitura de arquivos Excel

## Estrutura de Dados Esperada

O arquivo Excel deve conter uma aba chamada **"Relatório Anúncios patrocinados"** com colunas como:

- Data (Desde/Até)
- Campanha/Título do anúncio
- Impressões
- Cliques
- Investimento (moeda local)
- Receita (moeda local)
- CPC, CTR, ROAS, ACOS (opcionais, serão calculados)

## Desenvolvimento

O projeto separa claramente as responsabilidades:

- **HTML/JavaScript**: Interface, visualizações, manipulação de arquivos
- **Python**: Lógica de negócio, processamento de dados, cálculos de métricas

Esta arquitetura facilita a manutenção e permite que desenvolvedores Python trabalhem na lógica de dados sem precisar mexer no frontend.
