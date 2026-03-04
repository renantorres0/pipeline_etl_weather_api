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

    extract() >> transform() >> load()

weather_pipeline()

