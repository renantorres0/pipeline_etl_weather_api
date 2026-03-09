from datetime import datetime, timedelta
from airflow.decorators import dag, task
from pathlib import Path
import sys, os

sys.path.insert(0, '/opt/airflow/src')

from extract_data import extract_weather_data
from load_data import load_weather_data
from transform_data import data_transformations
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / 'config' / '.env'
load_dotenv(env_path)

API_KEY = os.getenv('API_KEY')

WEBHOOK_TOKEN = os.getenv('WEBHOOK_TOKEN', '123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ')

WEBHOOK_URL = os.getenv('DASHBOARD_WEBHOOK_URL', 'http://host.docker.internal:8502/webhook/dag-success')

url = f"https://api.openweathermap.org/data/2.5/weather?q=Sao Paulo,BR&units=metric&appid={API_KEY}"

@dag(
    dag_id='weather_pipeline',
    default_args={
        'owner': 'airflow',
        'depends_on_past': False,
        'retries': 2,
        'retry_delay': timedelta(minutes=5),
    },
    description='Pipeline ETL - Clima SP',
    schedule='0 */1 * * *',
    start_date=datetime(2024, 6, 1),
    catchup=False,
    tags=['weather', 'ETL']
)

def weather_pipeline():
    @task()
    def extract():
        extract_weather_data(url)

    @task()
    def transform():
        df = data_transformations()
        df.to_parquet('/opt/airflow/data/sp_weather.parquet', index=False)

    @task()
    def load():
        import pandas as pd
        df = pd.read_parquet('/opt/airflow/data/sp_weather.parquet')
        load_weather_data('sp_weather', df)

    @task()
    def notify_dashboard(dag_id: str = 'weather_pipeline', run_id: str = 'manual'):
        """"Dispara webhook para atualizar dashboard Streamlit"""
        import requests
        import logging
        
        logger = logging.getLogger(__name__)
        
        payload = {
            "token": WEBHOOK_TOKEN,
            "dag_id": dag_id,
            "run_id": run_id
        }
        
        try:
            response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook triggered successfully: {response.status_code}")
        except requests.exceptions.ConnectionError:
            logger.warning("Failed to connect to the webhook URL. Dashboard update may be delayed.")
        except Exception as e:
            logger.error(f"Error triggering webhook: {e}")

    extract() >> transform() >> load() >> notify_dashboard()

weather_pipeline()

