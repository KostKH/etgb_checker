from dataclasses import asdict

from flask import Flask, jsonify, request
from markupsafe import escape

from core_layer.models import Queries
from core_layer.tasks import generate_id, get_etgb
from db_layer.database import QueryRepository
from helpers.status_codes import StatusCode

app = Flask(__name__)


@app.route('/')
def hello() -> str:
    return 'Greetings from etgb_checker app!'


@app.route('/etgb', methods=['POST'])
def search_for_etgb():
    """Функция для обработки запроса к ендпойнту на получение деклараций."""
    errors = {key: 'required' for key in ('ozon_client_id', 'ozon_api_key')
              if key not in request.json.keys()}
    if errors:
        return jsonify({'status': 'FAIL', 'details': errors}), 400
    query_rep = QueryRepository()
    query_id = generate_id(25, query_rep)
    query = Queries(id=query_id)
    query_rep.add(query)
    get_etgb.delay(
        ozon_client_id=request.json.get('ozon_client_id'),
        ozon_api_key=request.json.get('ozon_api_key'),
        query_id=query_id)

    data = {
        'status_code': StatusCode.PROCESSING.value,
        'status_text': StatusCode.PROCESSING.name,
        'request_id': query_id,
        'request_URL': f'/etgb/{query_id}'
    }
    return jsonify(data), 202


@app.route('/etgb/<string:query_id>')
def get_query_info(query_id):
    """Функция возвращает информацию о статусе конкретного запроса,
    чей id указан в ендпойнте."""
    query_rep = QueryRepository()
    query_item = query_rep.get(id=escape(query_id))
    if not query_item:
        return jsonify({'status': 'NOT_FOUND', }), 404
    data = asdict(query_item)
    return jsonify(data), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
