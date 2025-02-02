from flask import Flask, redirect, url_for, session, render_template, request, flash, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from request_methods import request_constructor
from gcp_methods import get_all_folders, get_folder, get_documents, set_private_document
import os
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "X9zfwB$hXKp@LScb"

# Configuración de OAuth
# SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
SCOPES = ['https://www.googleapis.com/auth/drive']
CLIENT_SECRETS_FILE = "credentials.json"


# ────────────────────────────────────
# 📌 Core Flask
# ────────────────────────────────────


@app.route('/')
def home():
    if 'token' in session:
        return redirect(url_for('main_page'))

    if not os.path.exists(CLIENT_SECRETS_FILE):
        flash("⚠️ Error: El archivo credentials.json no existe. Cárgalo en la carpeta del proyecto.")
        return render_template('index.html', error=True)

    return render_template('index.html', error=False)


@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri=url_for('callback', _external=True)
    )
    auth_url, state = flow.authorization_url(prompt='consent')
    session['state'] = state

    return redirect(auth_url)


@app.route('/callback')
def callback():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES,
        redirect_uri=url_for('callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['token'] = creds_to_dict(creds)

    return redirect(url_for('main_page'))


@app.route('/logout')
def logout():
    """Cierra sesión eliminando el token."""
    session.pop('token', None)
    return redirect(url_for('home'))


# ────────────────────────────────────
# 📌 Transversales
# ────────────────────────────────────

@app.route('/main')
def main_page():
    validate_token()
    return render_template('main-page.html')


def validate_token():
    if 'token' not in session:
        return redirect(url_for('login'))


def get_credentials():
    creds = Credentials(**session['token'])
    return creds


def creds_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }


# ────────────────────────────────────
# 📌 Core Transaccional
# ────────────────────────────────────


@app.route('/list_folders')
def list_folders():
    validate_token()
    credentials = get_credentials()

    folders = []
    response_list_folders, data = get_all_folders(credentials)
    if response_list_folders is True:
        folders = data
    else:
        flash(message=data)

    return render_template('folders.html', folders=folders)


@app.route('/search_folder', methods=['GET'])
def search_folder():
    validate_token()
    folders = None
    folder_name = request.args.get('name')
    if not folder_name:
        flash("⚠️ Debes proporcionar un nombre de carpeta para buscar.")
        return redirect(url_for('main_page'))

    credentials = get_credentials()

    response, data = get_folder(credentials, folder_name)
    if response is True:
        folders = data
    else:
        flash(message=data)

    if not folders:
        flash(f"❌ No se encontraron carpetas con el nombre '{folder_name}'.")
        return redirect(url_for('home'))

    return render_template('search_folder.html', folders=folders, search_query=folder_name)


def get_documents_transversal(credentials, folder_id=None):
    documents = []
    response, data, message_db = get_documents(credentials, folder_id)
    if response is True:
        documents = data
        flash(message=message_db)
    else:
        flash(message=data)

    return render_template('documents.html', documents=documents)


@app.route('/search_documents')
def search_documents():
    validate_token()
    credentials = get_credentials()
    return get_documents_transversal(credentials)


@app.route('/search_document_id', methods=['GET'])
def search_files_in_folder():
    validate_token()
    credentials = get_credentials()
    folder_id = request.args.get('folder_id')
    if not folder_id:
        flash("⚠️ Debes proporcionar un id de carpeta para buscar los documentos.")
        return redirect(url_for('main_page'))

    return get_documents_transversal(credentials, folder_id)


@app.route('/list_public_documents', methods=['GET'])
def get_public_documents():
    documents = []
    response, message = request_constructor('GET')
    if response is True:
        documents = message
    else:
        flash(message=message)

    if not documents:
        flash("❌ No se encontraron documentos")

    return render_template('public_documents.html', documents=documents)


@app.route('/update/individual', methods=['PUT'])
def update_document():
    data_to_update = request.get_json()
    validate_token()
    credentials = get_credentials()
    result, message = set_private_document(credentials, data_to_update)
    logger.info('message response update')
    logger.info(message)

    if result:
        return jsonify({
            "message": message,
            "status": "success"
        }), 200
    else:
        return jsonify({
            "message": message,
            "status": "error"
        }), 400


if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0', ssl_context=('./certs/cert.pem', './certs/key.pem'))
