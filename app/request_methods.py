import requests
from requests import Response
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from global_exception_log import error_logger

DATABASE_MS_URL = "https://db-ms-challenge:5000/documents"


def request_constructor(method, data=None):
    headers = {
        'Content-Type': 'application/json'
    }
    response : Response
    try:
        if method == 'POST':
            response = requests.post(f'{DATABASE_MS_URL}/save', json=data, headers=headers, verify=False)
        elif method == 'PUT':
            response = requests.put(f'{DATABASE_MS_URL}/update', json=data, headers=headers, verify=False)
        else:
            response = requests.get(f'{DATABASE_MS_URL}/get', headers=headers, verify=False)

        if response.status_code == 200:
            logger.info('Respuesta exitosa API')
            logger.info(response.json())
            return True, response.json()['message']
        else:
            logger.info('Respuesta errada API')
            logger.info(response.json())
            return False, response.json()['message']

    except requests.exceptions.RequestException as e:
        message = f"Error en la petición: {e}"
        error_logger(e, message)
        return False, message
