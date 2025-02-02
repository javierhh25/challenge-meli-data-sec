from flask import Flask, request, jsonify
from typing import Union, List, Dict
from database_methods import get_public_documents, validate_insert_documents, update_registers
from decorators import json_handler

app = Flask(__name__)

@app.route('/', methods=["GET"])
def health_check():
    return jsonify(message="Work"), 200


@app.route('/documents/save', methods=['POST'])
@json_handler
def create_documents(data: Union[List, Dict]):
    return  validate_insert_documents(data)


@app.route('/documents/update', methods=['PUT'])
@json_handler
def update_documents(data: Union[List, Dict]):
    return  update_registers(data)


@app.route('/documents/get', methods=['GET'])
def get_documents():
    result, message =  get_public_documents()

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

