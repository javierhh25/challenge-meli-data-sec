import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('global_error_logger')

def error_logger(e: Exception, message: str):
    logger.info(message)
    tb = e.__traceback__
    line_number = tb.tb_lineno
    file_name = tb.tb_frame.f_code.co_filename
    logger.info(e)
    logger.info(f'Line number: {line_number} File: {file_name} Error: {str(e)}') 