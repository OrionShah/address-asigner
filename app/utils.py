import hashlib
import os
import pickle
from pathlib import Path
from urllib.parse import urlencode

import requests
from redis import Redis

from app.settings import regions, REDIS_HOST

Y_APIKEY = 'c811583b-f5cc-4274-9aa9-f4ae01a3cbfa'


# def _del_cache(url):
#     url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
#     cachefile = Path(f'cache/{url_hash}.pickle')
#     if cachefile.exists():
#         os.remove(cachefile.absolute())


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

def _del_cache(url):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    redis_key = f'cache-{url_hash}'
    redis = Redis(host=REDIS_HOST)
    redis.delete(redis_key)


def _get(url, update=False):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    redis_key = f'cache-{url_hash}'
    redis = Redis(host=REDIS_HOST)
    redis_data = redis.get(redis_key)
    if redis_data and not update:
        content = pickle.loads(redis_data)
    else:
        content = requests.get(url)
        if content.status_code != 200:
            return content
        redis.set(redis_key, pickle.dumps(content))
    return content


def get_coords(address):
    pos = ()
    params = urlencode({'apikey': Y_APIKEY, 'geocode': address,
                        'format': 'json'})
    url = f'https://geocode-maps.yandex.ru/1.x/?{params}'
    response = _get(url).json()
    if 'response' not in response.keys():
        _del_cache(url)
        return pos

    member = response['response']['GeoObjectCollection']['featureMember']
    if len(member):
        pos = member[0]['GeoObject']['Point']['pos'].split(' ')

    return pos[::-1]

def get_uik(value):
    response = _get(f'http://www.cikrf.ru/services/lk_address/{value}?do=result').content.decode('CP1251')
    substr = 'Участковая избирательная комиссия №'
    start = response.find(substr)
    if start == -1:
        return -1
    end = response[start:].find('<')
    uik = response[start+len(substr):start+end]
    return int(uik)
