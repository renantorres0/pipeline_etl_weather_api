# Weather Pipeline ETL

Pipeline de dados automatizado que coleta, transforma e armazena dados meteorológicos de São Paulo em tempo real, com orquestração via Apache Airflow e stack completa em Docker.

---

## Visão Geral da Arquitetura

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   OpenWeatherMap    │────▶│   Apache Airflow      │────▶│    PostgreSQL 16    │
│       API           │     │  (CeleryExecutor)     │     │    weather_data     │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
                                      │
                            ┌─────────┴────────┐
                            │                  │
                     ┌──────▼──────┐    ┌──────▼──────┐
                     │    Redis    │    │   Celery    │
                     │  (Broker)   │    │  (Workers)  │
                     └─────────────┘    └─────────────┘
```

## Fluxo do Pipeline

```
extract()  ──▶  transform()  ──▶  load()
   │                │               │
   ▼                ▼               ▼
weather_         sp_weather.    sp_weather
data.json         parquet      (PostgreSQL)
```

---

## Tecnologias

| Categoria | Tecnologia |
|-----------|-----------|
| Orquestração | Apache Airflow 3.1.7 |
| Containerização | Docker + Docker Compose |
| Banco de Dados | PostgreSQL 16 |
| Message Broker | Redis 7.2 |
| Linguagem | Python 3.12+ |
| Manipulação de Dados | Pandas 3.0+ |
| ORM / Conexão BD | SQLAlchemy + Psycopg2 |
| API de Dados | OpenWeatherMap API |
| Formato intermediário | Parquet + JSON |

---

## Estrutura do Projeto

```
weather_project/
├── config/
│   ├── .env                 # Credenciais e chave da API
│   └── airflow.cfg          # Configurações do Airflow
├── dags/
│   └── weather_dag.py       # Definição do DAG (pipeline principal)
├── data/
│   ├── weather_data.json    # Dados brutos extraídos da API
│   └── sp_weather.parquet   # Dados transformados (formato colunar)
├── notebooks/
│   └── analysis_data.ipynb  # Análise exploratória dos dados
├── src/
│   ├── extract_data.py      # Módulo de extração (API → JSON)
│   ├── transform_data.py    # Módulo de transformação (JSON → Parquet)
│   └── load_data.py         # Módulo de carga (Parquet → PostgreSQL)
├── docker-compose.yaml      # Stack completa de serviços
├── pyproject.toml           # Metadados e dependências do projeto
└── requirements.txt         # Dependências Python
```

---

## Pipeline em Detalhe

### 1. Extract — `src/extract_data.py`

Consome a OpenWeatherMap API para São Paulo/BR com as seguintes configurações:

- Unidades: métricas (Celsius, m/s)
- Saída: `data/weather_data.json`
- Validação de status HTTP antes de persistir

### 2. Transform — `src/transform_data.py`

Aplica uma sequência de transformações sobre o JSON bruto:

- Normaliza estruturas aninhadas com `pd.json_normalize()`
- Extrai e concatena o array `weather[]`
- Remove colunas irrelevantes (`weather_icon`, `sys.type`)
- Renomeia 38+ campos para nomenclatura legível
- Converte timestamps Unix para o fuso horário `America/Sao_Paulo`
- Saída: `data/sp_weather.parquet`

### 3. Load — `src/load_data.py`

- Lê o Parquet gerado na etapa anterior
- Conecta ao PostgreSQL via SQLAlchemy
- Insere os dados em modo `append` na tabela `sp_weather`
- Preserva todo o histórico de coletas

---

## Schema da Tabela `sp_weather`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `datetime` | TIMESTAMP | Data e hora da coleta (fuso SP) |
| `city_name` | TEXT | Nome da cidade |
| `temperature` | FLOAT | Temperatura atual (°C) |
| `feels_like` | FLOAT | Sensação térmica (°C) |
| `temp_min` | FLOAT | Temperatura mínima (°C) |
| `temp_max` | FLOAT | Temperatura máxima (°C) |
| `humidity` | INT | Umidade relativa (%) |
| `pressure` | INT | Pressão atmosférica (hPa) |
| `wind_speed` | FLOAT | Velocidade do vento (m/s) |
| `wind_deg` | INT | Direção do vento (graus) |
| `clouds` | INT | Cobertura de nuvens (%) |
| `visibility` | INT | Visibilidade (metros) |
| `weather_main` | TEXT | Categoria do tempo (Clear, Clouds…) |
| `weather_description` | TEXT | Descrição detalhada |
| `sunrise` | TIMESTAMP | Nascer do sol |
| `sunset` | TIMESTAMP | Pôr do sol |
| `latitude` | FLOAT | Latitude |
| `longitude` | FLOAT | Longitude |

> A tabela conta com 26 colunas no total. Apenas as principais estão listadas acima.

---

## Configuração do DAG

| Parâmetro | Valor |
|-----------|-------|
| DAG ID | `weather_pipeline` |
| Schedule | A cada hora (`0 */1 * * *`) |
| Start date | 2024-06-01 |
| Catchup | Desabilitado |
| Retries | 2 (intervalo de 5 min) |
| Tags | `weather`, `ETL` |

---

## Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Chave de API gratuita em [openweathermap.org](https://openweathermap.org/api)

### 1. Clone o repositório

```bash
git clone https://github.com/renantorres0/weather_project.git
cd weather_project
```

### 2. Configure as variáveis de ambiente

Crie o arquivo `config/.env`:

```env
API_KEY=sua_chave_openweathermap
database=weather_data
user=seu_usuario
password=sua_senha
```

### 3. Suba a stack

```bash
docker compose up -d
```

### 4. Acesse o Airflow

Abra [http://localhost:8080](http://localhost:8080) e ative o DAG `weather_pipeline`.

> Credenciais padrão: `airflow` / `airflow`

### 5. Monitore (opcional)

O Flower (monitoramento do Celery) está disponível em [http://localhost:5555](http://localhost:5555).

---

## Serviços Docker

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| Airflow Webserver | 8080 | Interface de gerenciamento dos DAGs |
| Flower | 5555 | Monitoramento dos workers Celery |
| PostgreSQL | 5433 | Banco de dados |
| Redis | 6379 | Message broker |

---

## Exemplo de Dado Coletado

```json
{
  "datetime": "2024-12-02 03:07:26-03:00",
  "city_name": "São Paulo",
  "temperature": 18.11,
  "feels_like": 18.33,
  "humidity": 90,
  "pressure": 1016,
  "wind_speed": 2.06,
  "weather_main": "Clear",
  "weather_description": "clear sky",
  "clouds": 0,
  "visibility": 10000
}
```

---

## Autor

Desenvolvido por **Renan Torres**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/renan-torres-121a06106/)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/renantorres0)