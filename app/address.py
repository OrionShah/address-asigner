import pickle

from redis import Redis

from app import tasks
from app.settings import REDIS_HOST
from app.utils import _get, get_uik

LIMITS = False

BASE_URL = 'http://www.cikrf.ru/services/lk_tree/'


def get_children(service_id=None, base_uri=None):
    params = f'id={service_id}' if service_id else 'first=1'
    children = []
    data = get_data(params)
    if len(data) == 1 and type(data[0]['children']) is list:
        data = data[0]['children']
    for child in data:
        url = f'{base_uri}-{child["id"]}' if base_uri else child['id']
        children.append({'id': child['id'], 'text': child['text'],
                         'level': int(child['a_attr']['levelid']),
                         'intid': child['a_attr']['intid'], 'url': url})
    return children


def start_process(service_id, address):
    process_node(get_children(service_id), address)


def prepare_parents(services):
    address = {}

    elements = get_data('first=1')[0]['children']
    while len(address) != len(services):
        for elem in elements:
            if elem['id'] in services:
                address.update({int(elem['a_attr']['levelid']): elem['text']})
                elements = get_data(f'id={elem["id"]}')
                break
    return address


def process_node(values, address: dict = {}):
    for value in values:
        response = get_data(f"id={value['id']}")
        level_id = value['level']
        address.update({level_id: value['text']})

        address = {key: address[key] for key in address.keys() if int(key) <= level_id}
        if len(response):
            tasks.process_node.delay(value['id'], address)
        else:
            tasks.save_address.delay(value, address)


def save(value, address):
    address_str = ', '.join(address.values())
    uik = get_uik(value['intid'])

    address = {'components': address, 'uik': uik, 'name': address_str,
               'intid': value['intid']}

    redis = Redis(host=REDIS_HOST)
    detail_key = f'address-{address_str}'
    redis.set(detail_key, pickle.dumps(address))
    if uik == -1:
        return

    redis.lpush(f'uik-addresses-{uik}', pickle.dumps(address))
    if not redis.get(f'uik-{uik}') and '2' in address['components'].keys():
        tasks.save_uik.delay(uik, address['components']['2'])


def get_data(params=''):
    content = _get(f'{BASE_URL}?{params}')
    return content.json()
