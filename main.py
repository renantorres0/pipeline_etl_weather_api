# from src.extract_data import extract_weather_data
# from src.load_data import load_weather_data
# from src.transform_data import data_transformations

# import os
# from pathlib import Path
# from dotenv import load_dotenv

# import logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# env_path = Path(__file__).resolve().parent / 'config' / '.env'
# load_dotenv(env_path)

# API_KEY = os.getenv('API_KEY')

# url = f"https://api.openweathermap.org/data/2.5/weather?q=Sao Paulo,BR&units=metric&appid={API_KEY}"
# table_name = 'sp_weather'

# def pipeline():
#     try:
#         logging.info("STEP 1: Extracting data from API")
#         extract_weather_data(url)
        
#         logging.info("STEP 2: Transforming data")
#         df = data_transformations()
        
#         logging.info("STEP 3: Loading data into database")
#         load_weather_data(table_name, df)
        
#         print("\n" + "="*60)
#         print("Pipeline executed successfully!")
#         print("="*60 + "\n")
        
#     except Exception as e:
#         logging.error(f"Pipeline execution failed: {e}")
#         import traceback
#         traceback.print_exc()

# pipeline()

