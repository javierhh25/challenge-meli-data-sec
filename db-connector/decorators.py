from flask import jsonify, request
from functools import wraps
from typing import Callable


def json_handler(function: Callable):
    """
    Decorador que maneja la validación de JSON antes de ejecutar la función principal
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            if not request.is_json:
                return jsonify({
                    "error": "El contenido debe ser JSON",
                    "status": "error"
                }), 400

            data = request.get_json()

            if data is None:
                return jsonify({
                    "message": "No se recibieron datos",
                    "status": "error"
                }), 400

            success, message = function(data, *args, **kwargs)

            if success is True:
                return jsonify({
                    "message": message,
                    "status": "success"
                }), 200
            else:
                return jsonify({
                    "message": message,
                    "status": "error"
                }), 400

        except Exception as e:
            return jsonify({
                "message": str(e),
                "status": "error"
            }), 500

    return wrapper