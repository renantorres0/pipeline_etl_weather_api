import requests
import json
from pathlib import Path

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_weather_data(url:str) -> list:
    respose = requests.get(url)
    data = respose.json()
    
    if respose.status_code != 200:
        logging.error("Erro na requisição")
        return []

    if not data:
        logging.warning("Nenhum dado encontrado")
        return []
    
    output_path = 'data/weather_data.json'
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4)
        
    logging.info("Dados extraídos e salvos com sucesso.")
    return data
