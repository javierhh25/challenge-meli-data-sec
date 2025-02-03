from googleapiclient.discovery import build

from email_methods import send_email
from global_exception_log import error_logger
from request_methods import request_constructor
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service_c = None


def service_constructor(credentials):
    global service_c
    if service_c is None:
        service_c = build('drive', 'v3', credentials=credentials)

    return service_c


def get_all_folders(credentials):
    try:
        service = service_constructor(credentials)

        folders = []
        query = "mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        page_token = None

        while True:
            results = service.files().list(
                q=query, fields="nextPageToken, files(id, name)",
                pageSize=1000, pageToken=page_token
            ).execute()

            folders.extend(results.get('files', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        return True, folders

    except Exception as e:
        message = 'Error obteniendo los folders'
        error_logger(e, message)
        return False, message


def get_folder(credentials, folder_name):
    try:
        service = service_constructor(credentials)

        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(
            q=query, fields="files(id, name)"
        ).execute()

        folders = results.get('files', [])

        return True, folders

    except Exception as e:
        message = f'Error obteniendo folder {folder_name}'
        error_logger(e, message)
        return False, message


def get_documents(credentials, folder_id=None):
    try:
        service = service_constructor(credentials)

        documents = []
        query = ""
        if folder_id:
            query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed=false"
        else:
            query = "mimeType != 'application/vnd.google-apps.folder' and trashed=false"

        page_token = None

        while True:
            results = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, owners, permissions, parents)",
                pageSize=1000, pageToken=page_token
            ).execute()

            for file in results.get('files', []):
                file_id = file['id']
                file_name = file['name']
                mime_type = file.get('mimeType', '')
                file_type = mime_type.split('.')[-1] if '.' in mime_type else mime_type.split('/')[-1]
                file_extension = file['name'].split('.')[-1]
                owner_email = file['owners'][0]['emailAddress'] if 'owners' in file else "Desconocido"
                parents = file.get('parents', [])

                is_public = any(
                    perm.get('type') == 'anyone' and perm.get('role') in ['reader', 'writer']
                    for perm in file.get('permissions', [])
                )
                visibility = "public" if is_public else "private"

                parent_name = "Raíz"
                if parents:
                    parent_id = parents[0]
                    parent_info = service.files().get(fileId=parent_id, fields="name").execute()
                    parent_name = parent_info.get('name', "Desconocido")

                documents.append({
                    "id_document": file_id,
                    "file_name": file_name,
                    "file_type": file_type,
                    "file_extension": file_extension,
                    "parent_name": parent_name,
                    "owner_email": owner_email,
                    "visibility": visibility
                })

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        _, message = request_constructor('POST', documents)

        return True, documents, message

    except Exception as e:
        message = 'Error obteniendo documentos'
        error_logger(e, message)
        return False, message, None


def set_private_document(credentials, data_to_update):
    try:
        service = service_constructor(credentials)
        permissions = service.permissions().list(fileId=data_to_update['id_document'], fields="permissions(id, role, type)").execute()

        public_permissions = [perm['id'] for perm in permissions.get('permissions', []) if perm['type'] == 'anyone']

        if not public_permissions:
            return False, 'Documento no es público'

        for perm_id in public_permissions:
            service.permissions().delete(fileId=data_to_update['id_document'], permissionId=perm_id).execute()
            logger.info("PERMISO PÚBLICO ELIMINADO")


    except Exception as e:
        message = 'Error cambiando la visibilidad del archivo'
        error_logger(e, message)

    result, message = request_constructor('PUT', [data_to_update])

    if result is True:
        send_email(data_to_update['owner_email'], data_to_update['file_name'], data_to_update['parent_name'])
        return True, message
    else:
        send_email(data_to_update['owner_email'], data_to_update['file_name'], data_to_update['parent_name'])
        return False, ('Se cambiaron los permisos en google drive, '
                       'pero no en la base de datos, por favor realiza una nueva validación de los documentos para que sea actualizada la visibilidad ')




