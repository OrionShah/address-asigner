# хранить в редисе как "номер участка"-"адрес"
from celery import Celery

from app import utils, address, population

app = Celery('tasks', broker='redis://redis:6379/0')


@app.task(queue='tasks')
def process_node(service_id, address_components: dict = {}):
    # обрабатывает адреса, собирая граф
    address.start_process(service_id, address_components)


@app.task(queue='tasks')
def save_address(value, address_components):
    address.save(value, address_components)


@app.task(queue='tasks')
def get_coords(detail_key):
    utils.get_coords(detail_key)
    # добавить адресу координаты


@app.task(queue='tasks')
def process_population(url):
    # собираем данные по жителям
    population.process_node(url)


@app.task(queue='tasks')
def process_uik(uik, region):
    # собрать инфу по избирательному участку
    utils.get_uik_info(uik, region)
