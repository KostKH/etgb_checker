import datetime as dt
import logging
import random
import string

import requests
from celery.utils.log import get_task_logger

import settings
# from celery import shared_task
from core_layer.celery import app
from core_layer.models import Results
from db_layer.database import QueryRepository, ResultsRepository
from helpers.errors_etgb import ResponseParseError, SaveResultsToDbError
from helpers.status_codes import StatusCode

logger = get_task_logger(__name__)


@app.task
def get_etgb(
    ozon_client_id,
    ozon_api_key,
    query_id,
) -> None:
    """Функция обращается к API Озона, получает декларации,
    с помощью вспомогательных функций сериализует данные и
    сохраняет их в репозитрий / базу данных."""
    results_repository = ResultsRepository()
    query_repository = QueryRepository()
    headers = {
        'Client-Id': str(ozon_client_id),
        'Api-Key': str(ozon_api_key)
    }
    date_to = dt.datetime.utcnow()
    date_from = date_to - dt.timedelta(days=settings.DELTA_DAYS)
    body = {
        'data': {
            'from': date_from.isoformat() + 'Z',
            'to': date_to.isoformat() + 'Z'
        },
    }
    try:
        response = requests.post(
            url=settings.OZON_API_URL,
            json=body,
            headers=headers)
    except Exception as e:
        logger.exception(e)
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.OZON_URL_IS_NOT_REACHED.value,
            status_text=StatusCode.OZON_URL_IS_NOT_REACHED.name,
        )
        return
    if response.status_code != 200:
        logger.error(
            f'{StatusCode.OZON_ERROR_STATUS_CODE}, {response.status_code}, '
            f'{response.text}')
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.OZON_ERROR_STATUS_CODE.value,
            status_text=StatusCode.OZON_ERROR_STATUS_CODE.name,
            ozone_response_code=response.status_code,
        )
        return

    try:
        etgb_data = response.json()
        parsed_etgb_data = parse_response(etgb_data)
        save_result = results_repository.add(parsed_etgb_data)
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.DONE.value,
            status_text=StatusCode.DONE.name,
            ozone_response_code=response.status_code,
            etgb_found_total=len(parsed_etgb_data),
            etgb_saved_new=save_result)

    except ResponseParseError as e:
        logger.exception(e)
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.RES_PARSE_ERROR.value,
            status_text=StatusCode.RES_PARSE_ERROR.name,
            ozone_response_code=response.status_code,
        )
        return
    except SaveResultsToDbError as e:
        logger.exception(e)
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.SAVE_TO_DB_ERROR.value,
            status_text=StatusCode.SAVE_TO_DB_ERROR.name,
            ozone_response_code=response.status_code,
        )
        return
    except Exception as e:
        logger.exception(e)
        update_query(
            rep=query_repository,
            query_id=query_id,
            status_code=StatusCode.OTHER_ERROR.value,
            status_text=StatusCode.OTHER_ERROR.name,
        )
        return


def parse_response(data: dict) -> list:
    """Вспомогательная функция для парсинга данных,
    полученных от Озона, создает на основе данных
    экземлпяры модели результатов. Возвращает список с
    моделями."""
    parsed_etgb_data = []
    inner_data = data.get('result')
    try:
        for item in inner_data:
            model_item = Results(
                posting_number=item['posting_number'],
                etgb_number=item['etgb']['number'],
                etgb_date=dt.date.fromisoformat(item['etgb']['date']),
                etgb_url=item['etgb']['url'],)
            parsed_etgb_data.append(model_item)
        return parsed_etgb_data
    except Exception as e:
        logger.exception('Ошибка при трансформации записи в модель. '
                         f'Запись: {item}, {e}')
        raise ResponseParseError(e)


def update_query(
    rep: QueryRepository,
    query_id: str,
    **kwargs,
) -> None:
    """Функция для обновления статуса запроса в репозитории / базе данных.
    Функция принимает на вход id запроса, объект репозитория и данные,
    которые нужно обновить. После этого функция запрашивает из репозитория
    объект запроса, меняет отдельные атрибуты запроса на те, что были
    переданы в функцию, и сохраняет результат в репозиторий."""
    if not kwargs:
        return
    try:
        query_model = rep.get(id=query_id)
        for key, value in kwargs.items():
            if key in query_model.__dict__.keys():
                setattr(query_model, key, value)
        rep.add(query_model)
        return
    except Exception as e:
        logging.exception(e)
        raise


def generate_id(length, query_repository):
    """Функция для генерации id запроса. id генерим, чтобы по запросам
    к API стороннему пользователю было сложнее понимать кол-во запросов."""
    letters_and_digits = string.ascii_lowercase + string.digits
    while True:
        request_id = ''.join(random.sample(letters_and_digits, length))
        result = query_repository.get(request_id)
        if not result:
            break
    return request_id
