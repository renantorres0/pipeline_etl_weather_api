from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

env_path = Path(__file__).resolve().parent.parent / 'config' / '.env'
load_dotenv(env_path, encoding='utf-8')

user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')
host = 'host.docker.internal'

def get_engine():
    logging.info(f"Creating database engine for user: {user}, database: {database}, host: {host}")
    return create_engine(
        f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:5433/{database}"
    )

engine = get_engine()

def  load_weather_data(table_name:str, df):
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists='append',
        index=False
    )
    
    logging.info(f"Data loaded into table '{table_name}' successfully.")
    
    df_check = pd.read_sql(f"SELECT * FROM {table_name}", con=engine)
    logging.info(f"Data in table '{table_name}':\n{df_check.head()}")
    
    
