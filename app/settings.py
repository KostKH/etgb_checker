import os


def get_query_db_params():
    return 'query_db/queries.db'


def get_results_db_params():
    return {
        'host': os.getenv('DB_CLICK_HOST', 'localhost'),
        'port': int(os.getenv('DB_CLICK_PORT', 19000)),
        'database': os.getenv('CLICKHOUSE_DB', 'default'),
        'user': os.getenv('CLICKHOUSE_USER', 'testuser'),
        'password': os.getenv('CLICKHOUSE_PASSWORD', 'KakoitoPass1'),
    }


OZON_API_URL = 'https://api-seller.ozon.ru/v1/posting/global/etgb'

DELTA_DAYS = 4

RABBITMQ = {
    'PROTOCOL': 'amqp',
    'HOST': os.getenv('RABBITMQ_HOST', 'localhost'),
    'PORT': os.getenv('RABBITMQ_PORT', 5672),
    'USER': os.getenv('RABBITMQ_DEFAULT_USER', 'etgbuser'),
    'PASSWORD': os.getenv('RABBITMQ_DEFAULT_PASS', 'oBd4xuOAROv2x0f5'),
}
CELERY_BROKER_URL = (f'{RABBITMQ["PROTOCOL"]}://{RABBITMQ["USER"]}:'
                     f'{RABBITMQ["PASSWORD"]}@{RABBITMQ["HOST"]}:'
                     f'{RABBITMQ["PORT"]}')
