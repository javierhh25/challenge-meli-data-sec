import mysql.connector
import os
from mysql.connector.abstracts import MySQLConnectionAbstract, MySQLCursorAbstract
from mysql.connector.pooling import PooledMySQLConnection
from dotenv import load_dotenv
from global_exception_log import error_logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database-ms')

dotenv_path = os.path.join(os.path.dirname(__file__), "deploy/secrets/.env")
load_dotenv(dotenv_path=dotenv_path)

db: PooledMySQLConnection | MySQLConnectionAbstract
cursor: MySQLCursorAbstract

CREATE_SENTENCE_TABLE_DOCUMENTS = """
    CREATE TABLE IF NOT EXISTS document (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_document VARCHAR(200) UNIQUE NOT NULL,
        file_name VARCHAR(200) NOT NULL,
        file_type VARCHAR(200) NOT NULL,
        file_extension VARCHAR(200) NOT NULL,
        parent_name VARCHAR(200) NOT NULL,
        owner_email VARCHAR(200) NOT NULL,
        visibility VARCHAR(200) NOT NULL,
        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL
    );

"""

CREATE_SENTENCE_TABLE_LOG_CHANGE = """
    CREATE TABLE IF NOT EXISTS log_change (
        id INT AUTO_INCREMENT PRIMARY KEY,
        id_document VARCHAR(200) NOT NULL,
        log_desc VARCHAR(200) NOT NULL,
        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        FOREIGN KEY (id_document) REFERENCES document(id_document) ON DELETE CASCADE
    );

"""

SELECT_PUBLIC_DOCUMENTS = "SELECT * FROM document WHERE visibility = 'public'; "


def close_connection_(close=True):
    if close is True:
        cursor.close()
        db.close()


def init_connection():
    global db, cursor

    db = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
    )

    cursor = db.cursor()


def get_table_status(table_name):
    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
    result = cursor.fetchone()

    if result:
        return True
    else:
        return False


def verify_tables():
    result = get_table_status('log_change')
    try:
        if result is False:
            logger.info('CREANDO DOCUMENTS')
            cursor.execute(CREATE_SENTENCE_TABLE_DOCUMENTS)
            logger.info("CREANDO LOGCHANGE")
            cursor.execute(CREATE_SENTENCE_TABLE_LOG_CHANGE)
            logger.info("CREADAS")
        return True, ''
    except Exception as e:
        db.rollback()
        return False, f"Error al creando las tablas: {e}"


def get_public_documents(query=SELECT_PUBLIC_DOCUMENTS, data=None, close_connection=True):
    if close_connection is True:
        init_connection()

    try:
        result, message = verify_tables()
        if result is True:
            if data:
                cursor.execute(query, tuple(data))
            else:
                cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            result = []
            for row in cursor.fetchall():
                result.append(dict(zip(columns, row)))
            return True, result
        else:
            return result, message
    except Exception as e:
        return False, f"Error obteniendo documentos: {e}"
    finally:
        close_connection_(close_connection)


def get_registers_by_id(ids):
    placeholders = ', '.join(['%s'] * len(ids))
    query = f"SELECT * FROM document WHERE id_document IN ({placeholders})"
    return get_public_documents(query, ids, False)


def exclude_existing_documents(all_documents, database_documents):
    ids_to_exclude = {document['id_document'] for document in database_documents}
    new_documents = []
    update_documents = []

    for document in all_documents:
        if document['id_document'] not in ids_to_exclude:
            new_documents.append(document)
        else:
            update_documents.append(document)

    return new_documents, update_documents


def validate_insert_documents(registers):
    ids = [document['id_document'] for document in registers]
    init_connection()
    response_registers, data_update = get_registers_by_id(ids)

    if response_registers is True:
        new_documents, update_documents = exclude_existing_documents(registers, data_update)

        response_update, message_update = update_registers(update_documents, False)
        if response_update is True:
            response_insert, message_insert = insert_documents(new_documents, False)

            if response_insert is True:
                return True, f'{message_update} y {message_insert}'
            else:
                return False, f'{message_update}, pero no se insertaron los documentos nuevos {message_insert}'
        else:
            return response_update, message_update

    else:
        return response_registers, data_update


def insert_documents(documents, close_connection=True):
    logger.info(f"INSERTING {len(documents)} registers")

    if close_connection is True:
        init_connection()

    if len(documents) == 0:
        return True, "No hay documentos para insertar"

    result, message = verify_tables()
    if result is True:
        query = """
        INSERT INTO document (id_document, file_name, file_type, file_extension, parent_name, owner_email, visibility)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        # Convertir la lista de diccionarios en una lista de tuplas
        values = [(doc['id_document'], doc['file_name'], doc['file_type'], doc['file_extension'], doc['parent_name'], doc['owner_email'], doc['visibility']) for
                  doc
                  in documents]

        try:
            cursor.executemany(query, values)
            db.commit()
            return True, f"{cursor.rowcount} documentos insertados exitosamente."
        except Exception as e:
            db.rollback()
            return False, f"Error al insertar los documentos: {e}"
        finally:
            close_connection_(close_connection)
    else:
        close_connection_(close_connection)
        return result, message


def update_registers(registers, close_connection=True):
    logger.info(f"UPDATING {len(registers)} registers")

    if close_connection:
        init_connection()

    fields_to_update = [
        'file_name',
        'file_type',
        'file_extension',
        'parent_name',
        'owner_email',
        'visibility'
    ]

    set_clause = ", ".join([f"{field} = %s" for field in fields_to_update])

    query_update = f"""
        UPDATE document
        SET {set_clause}
        WHERE id_document = %s
    """

    query_log = """
        INSERT INTO log_change (id_document, log_desc)
        VALUES (%s, %s)
    """

    values_update = []
    update_map = {}

    for record in registers:
        values_update.append((
            record['file_name'],
            record['file_type'],
            record['file_extension'],
            record['parent_name'],
            record['owner_email'],
            record['visibility'],
            record['id_document']
        ))
        update_map[record['id_document']] = record['visibility']

    try:
        cursor.executemany(query_update, values_update)

        updated_rows = cursor.rowcount
        logger.info(f"{updated_rows} registros actualizados en document")

        if updated_rows > 0:
            updated_docs_query = """
                SELECT id_document FROM document
                WHERE id_document IN ({})
            """.format(",".join(["%s"] * len(update_map)))

            cursor.execute(updated_docs_query, list(update_map.keys()))
            updated_ids = {row[0] for row in cursor.fetchall()}

            values_log = [
                (doc_id, f"Se cambia visibilidad a {update_map[doc_id].upper()}")
                for doc_id in updated_ids
            ]

            if values_log:
                cursor.executemany(query_log, values_log)
                logger.info(f"{len(values_log)} registros insertados en log_change")

        db.commit()
        return True, f"Se actualizaron {updated_rows} registros y se guardaron logs."

    except Exception as e:
        db.rollback()
        message = f"Error al actualizar los documentos y logs: {e}"
        error_logger(e, message)
        return False, message

    finally:
        close_connection_(close_connection)
