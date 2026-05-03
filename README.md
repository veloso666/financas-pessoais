<h1 align="center">
  💰 Finanças Pessoais
</h1>

<p align="center">
  Aplicativo web interativo para controle de gastos e investimentos pessoais
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white"/>
</p>

---

## Sobre o projeto

Nasceu de uma planilha simples de controle mensal e evoluiu para um app web completo com graficos interativos, categorias personalizadas e historico de evolucao financeira.

## Funcionalidades

| Pagina | Descricao |
|--------|-----------|
| **Dashboard** | Cards de Receitas, Gastos e Saldo + grafico de pizza por categoria + top gastos do mes |
| **Lancar** | Adicionar transacoes com suporte ao formato brasileiro (2.622,83) + excluir lancamentos |
| **Evolucao** | Graficos de barras e linha comparando todos os meses do ano + stack por categoria |
| **Categorias** | Criar e visualizar categorias com cores personalizadas |

## Tecnologias

- **[Streamlit](https://streamlit.io/)** - Interface web em Python puro
- **[PostgreSQL](https://www.postgresql.org/)** - Banco de dados relacional
- **[SQLAlchemy](https://www.sqlalchemy.org/)** - ORM para Python
- **[Plotly](https://plotly.com/python/)** - Graficos interativos
- **[pandas](https://pandas.pydata.org/)** - Manipulacao de dados

## Como rodar localmente

### Pre-requisitos

- Python 3.11+
- PostgreSQL instalado e rodando

### Passo a passo

```bash
# 1. Clone o repositorio
git clone https://github.com/veloso666/financas-pessoais.git
cd financas-pessoais

# 2. Crie o ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Instale as dependencias
pip install -r requirements.txt

# 4. Configure o banco de dados
# No PostgreSQL, crie o banco:
# CREATE DATABASE financas;

# 5. Configure as variaveis de ambiente
copy .env.example .env
# Edite o .env com suas credenciais

# 6. Rode o app
streamlit run app.py
```

Acesse **http://localhost:8501**

## Variaveis de ambiente

Crie um arquivo `.env` baseado no `.env.example`:

```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=financas
DB_USER=postgres
DB_PASSWORD=sua_senha
```

## Estrutura do projeto

```
financas-pessoais/
├── app.py              # App Streamlit - todas as paginas
├── db.py               # Models SQLAlchemy + conexao com PostgreSQL
├── requirements.txt    # Dependencias Python
├── .env.example        # Template das variaveis de ambiente
└── .gitignore
```

## Roadmap

- [x] V1 - Dashboard, lancamentos, evolucao anual, categorias
- [ ] V2 - Metas financeiras e alertas de limite por categoria
- [ ] V2 - Importacao de extrato bancario (CSV/OFX)
- [ ] V2 - Relatorio PDF mensal
- [ ] V3 - Multi-usuario com autenticacao

---

<p align="center">
  Feito por <a href="https://github.com/veloso666">Joao Lucas Veloso</a>
</p>