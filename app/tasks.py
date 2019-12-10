# хранить в редисе как "номер участка"-"адрес"
import pickle

from celery import Celery

from address import get_soap_data
from app import utils, address, population

app = Celery('tasks', broker='redis://redis:6379/0')


@app.task(queue='tasks', bind=True)
def process_node(self, service_id, address_components: dict = {}, **kwargs):
    # обрабатывает адреса, собирая граф
    try:
        address.start_process(service_id, address_components)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@app.task(queue='tasks', bind=True)
def save_address(self, value, address_components, **kwargs):
    try:
        address.save(value, address_components)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@app.task(queue='tasks', bind=True)
def get_coords(self, detail_key, **kwargs):
    # добавить адресу координаты
    try:
        utils.get_coords(detail_key)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@app.task(queue='tasks', bind=True)
def process_population(self, url, **kwargs):
    # собираем данные по жителям
    try:
        data = get_soap_data(url)
        population.process_node(data)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)


@app.task(queue='tasks', bind=True)
def process_uik(self, uik, region, **kwargs):
    # собрать инфу по избирательному участку
    try:
        utils.get_uik_info(uik, region)
    except Exception as exc:
        self.retry(exc=exc, countdown=30)
