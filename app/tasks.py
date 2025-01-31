# хранить в редисе как "номер участка"-"адрес"

from celery import Celery

from app import utils, address, population, settings

app = Celery('tasks', broker=f'redis://{settings.REDIS_HOST}:6379/0')

params = {'bind': True, 'queue': 'tasks', 'default_retry_delay': 30,
          'max_retries': 100, }


@app.task(**params)
def process_node(self, service_id, address_components: dict = {}, **kwargs):
    # обрабатывает адреса, собирая граф
    try:
        address.start_process(service_id, address_components)
    except Exception as exc:
        self.retry(exc=exc)


@app.task(**params)
def save_address(self, value, address_components, **kwargs):
    try:
        address.save(value, address_components)
    except Exception as exc:
        self.retry(exc=exc)


@app.task(**params)
def process_population(self, url, **kwargs):
    # собираем данные по жителям
    try:
        data = population.get_soap_data(url)
        population.process_node(data)
    except Exception as exc:
        self.retry(exc=exc)


@app.task(**params)
def save_uik(self, uik, region, **kwargs):
    # собрать инфу по избирательному участку
    try:
        population.get_uik_info(uik, region)
    except Exception as exc:
        self.retry(exc=exc)


@app.task(**params)
def process_uik(self, uik):
    try:
        population.process_people(uik)
    except Exception as exc:
        self.retry(exc=exc)
