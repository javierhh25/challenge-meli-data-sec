import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from global_exception_log import error_logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dotenv_path = os.path.join(os.path.dirname(__file__), "deploy/secrets/.env")
load_dotenv(dotenv_path=dotenv_path)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")


def send_email(to_email, file_name, parent_folder):
    message = Mail(
        from_email="fakepaquito@gmail.com",
        to_emails=to_email,
        subject="Cambio de visibilidad de documento",
        html_content=f"""
        
        Buen día,
        
        Se ha cambiado el acceso del archivo <strong>{parent_folder}/{file_name}</strong> a privado"""
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Correo enviado con status code: {response.status_code}")
    except Exception as e:
        message = f"Error al enviar el correo: {e}"
        error_logger(e, message)
