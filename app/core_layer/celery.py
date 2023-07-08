from celery import Celery

from settings import CELERY_BROKER_URL

app = Celery(
    'core_layer',
    broker=CELERY_BROKER_URL,
    include=['core_layer.tasks'])
