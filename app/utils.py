import hashlib
import os
import pickle
from pathlib import Path
from urllib.parse import urlencode

import requests
from redis import Redis

from app.settings import regions, REDIS_HOST

Y_APIKEY = 'c811583b-f5cc-4274-9aa9-f4ae01a3cbfa'


def _del_cache(url):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    cachefile = Path(f'cache/{url_hash}.pickle')
    if cachefile.exists():
        os.remove(cachefile.absolute())


# def _get(url, update=False):
#     # cachedir = Path('cache')
#     # if not cachedir.exists():
#     #     cachedir.mkdir()
#     url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
#     cachefile = Path(f'cache/{url_hash}.pickle')
#     if cachefile.exists() and not update:
#         with open(cachefile.absolute(), 'rb') as f:
#             # print(f'load cache {url}')
#             try:
#                 content = pickle.load(f)
#                 # process.update(1)
#             except EOFError:
#                 _del_cache(url)
#                 update = True
#         if update or content.status_code != 200:
#             # print(f'force update cache {url}')
#             return _get(url, True)
#     else:
#         # print(f'{os.getpid()} GET {url}')
#         content = requests.get(url)
#         if content.status_code != 200:
#             # print(f'cache not save {url}')
#             return content
#         with open(cachefile.absolute(), 'wb') as f:
#             pickle.dump(content, f)
#     return content

def _get(url, update=False):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    redis_key = f'cache-{url_hash}'
    redis = Redis(host=REDIS_HOST)
    redis_data = redis.get(redis_key)
    if redis_data and not update:
        print('cache')
        content = pickle.loads(redis_data)
    else:
        print('not cache')
        content = requests.get(url)
        if content.status_code != 200:
            return content
        redis.set(redis_key, pickle.dumps(content))
    return content


def get_coords(detail_key):
    redis = Redis(host=REDIS_HOST)
    address = pickle.loads(redis.get(detail_key))

    # TODO: проверять флаг в редисе и сразу переставлять задачу на начало суток

    pos = ()
    params = urlencode({'apikey': Y_APIKEY, 'geocode': address['name'],
                        'format': 'json'})
    url = f'https://geocode-maps.yandex.ru/1.x/?{params}'
    response = _get(url).json()
    if 'response' not in response.keys():
        _del_cache(url)
        # TODO: откладывать задачу до начало суток, выставлять флаг в редисе
        raise Exception('Координаты не получены')

    member = response['response']['GeoObjectCollection']['featureMember']
    if len(member):
        pos = member[0]['GeoObject']['Point']['pos'].split(' ')

    address.update({'coords': pos})
    redis.set(detail_key, pickle.loads(address))


def get_uik(value):
    response = _get(f'http://www.cikrf.ru/services/lk_address/{value}?do=result').content.decode('CP1251')
    substr = 'Участковая избирательная комиссия №'
    start = response.find(substr)
    if start == -1:
        return -1
    end = response[start:].find('<')
    uik = response[start+len(substr):start+end]
    return int(uik)


def get_uik_info(uik, region):
    region_code = get_region_code(region)
    url = f'http://www.cikrf.ru/iservices/voter-services/committee/subjcode/{region_code}/num/{uik}'
    data = _get(url).json()

    redis = Redis(host=REDIS_HOST)
    redis.set(f'uik-{uik}', pickle.dumps(data))


def get_region_code(region):
    return regions[region]
