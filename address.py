import hashlib
import pickle
import re
import os
from multiprocessing.pool import Pool
from pathlib import Path

from urllib.parse import urlencode

import typing

import requests
from pprint import pprint

from bs4 import BeautifulSoup
from tqdm import tqdm

# LIMITS = 11
LIMITS = False
Y_APIKEY = 'c811583b-f5cc-4274-9aa9-f4ae01a3cbfa'

YA_ERROR = True

# cached = Path(f'cache/')
# process = tqdm(total=len(os.listdir('cache')))


def get_data(url, id=''):
    content = _get(f'{url}{id}')
    return content.json()


def _del_cache(url):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    cachefile = Path(f'cache/{url_hash}.pickle')
    if cachefile.exists():
        os.remove(cachefile.absolute())


def _get(url, update=False):
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
    cachefile = Path(f'cache/{url_hash}.pickle')
    if cachefile.exists() and not update:
        with open(cachefile.absolute(), 'rb') as f:
            # print(f'load cache {url}')
            try:
                content = pickle.load(f)
                # process.update(1)
            except EOFError:
                _del_cache(url)
                update = True
        if update or content.status_code != 200:
            print(f'force update cache {url}')
            return _get(url, True)
    else:
        print(f'{os.getpid()} GET {url}')
        content = requests.get(url)
        if content.status_code != 200:
            print(f'cache not save {url}')
            return content
        with open(cachefile.absolute(), 'wb') as f:
            pickle.dump(content, f)
    return content


def get_uik(value):
    response = _get(f'http://www.cikrf.ru/services/lk_address/{value}?do=result').content.decode('CP1251')
    substr = 'Номер Территориальной избирательной комиссии: '
    start = response.find(substr)
    if start == -1:
        breakpoint()
        return -1
    end = response[start:].find('<')
    uik = response[start+len(substr):start+end]
    return int(uik)


def tree(values, address: dict = {}, deep=0):
    result = {}
    i = 0
    # print(deep, len(values))
    if deep == -1:
    # if deep == 5:
        with Pool(40) as pool:
            res = []
            for value in values:
                res.append(pool.apply_async(_tree, (value, address, deep)))
                i += 1
                if LIMITS and i > LIMITS:
                    break
            for ret in res:
                result.update(ret.get())
    else:
        for value in values:
            result.update(_tree(value, address, deep))
            i += 1
            if LIMITS and i > LIMITS:
                break
    return result


def _tree(value, address, deep):
    try:
        response = get_data('http://www.cikrf.ru/services/lk_tree/?id=',
                            value['id'])
    except:
        return {}
    level_id = int(value['a_attr']['levelid'])
    address.update({level_id: value['text']})

    address = {key: address[key] for key in address.keys() if key <= level_id}
    if len(response):
        return tree(response, address, deep+1)
    else:
        coords = _get_coords(', '.join(address.values()))
        uik = get_uik(value['a_attr']['intid'])
        return {tuple(address.values()): (uik, coords)}


def _get_coords(address):
    pos = ()
    if YA_ERROR:
        return pos
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
    return pos


def get_uiks_address():
    data = get_data('http://www.cikrf.ru/services/lk_tree/?', 'first=1&id=%23')
    data = [data[0]['children'][37]]
    # data = data[0]['children'][0]
    res = tree(data, {})
    uiks = {}
    for address, uik_coords in res.items():
        uik, coords = uik_coords
        key = tuple(list(address)[:-1])
        if len(key[-1]) > 5:
            uiks.update({address: {'coords': coords, 'place': [],
                                   'uiks': [uik]}})
            continue
        if key not in uiks.keys():
            uiks.update({key: {'coords': coords, 'place': [], 'uiks': []}})
        uiks[key]['place'].append(list(address)[-1])
        uiks[key]['uiks'] = list(set(uiks[key]['uiks']+[uik]))
    # pprint(res)
    return uiks


def option_replace(value=''):
    return value.replace(';', '&')


def get_soap_data(url=''):
    # data = requests.get(url).content.decode('cp1251')
    data = _get(url).content.decode('cp1251')
    return BeautifulSoup(data, features="html.parser")


def find_next(soap):
    for link in soap.find_all('a'):
        if link.text == 'сайт избирательной комиссии субъекта Российской Федерации':
            return option_replace(link['href'])
        if link.text == 'Итоги голосования':
            return option_replace(link['href'])
    if len(soap.find_all('option')):
        return 'ok'
    return None


def get_result(soap):
    # for link in soap.find_all('a'):
    #     if link.text == 'Итоги голосования':
    #         page_result = get_soap_data(option_replace(link.get('href')))
    block_result = soap.find('td', text=re.compile(
        'Число избирателей, включенных в список избирателей'))
    result = 0
    if block_result:
        result = int(block_result.parent.find('b').text)
    # else:
    #     breakpoint()
    for link in soap.find_all('a'):
        if link.text == 'Итоги голосования':
            page_result = get_soap_data(option_replace(link.get('href')))
            res = get_result(page_result)
            if res:
                result = res
    return result


def soap_tree(soap):
    result = {}
    i = 0
    if not soap.find_all('option'):
        pass

    for option in soap.find_all('option'):
        if option.text == '---':
            continue

        data = get_soap_data(option_replace(option['value']))
        next_page = find_next(data)
        if next_page == 'ok':
            result.update(soap_tree(data))
        elif not next_page:
            key = option.text[option.text.find('№')+1:]
            # breakpoint()
            result.update({int(key): {'people': get_result(data)}})
        else:
            child_data = {'next': soap_tree(get_soap_data(next_page)), 'people': get_result(data)}
            # breakpoint()
            result.update({option.contents[0]: child_data})
        i += 1
        if LIMITS and i > LIMITS:
            break

    return result


def get_population():
    url = 'http://www.volgograd.vybory.izbirkom.ru/region/volgograd?action=show&root_a=342000014&vrn=100100084849062&region=34&global=true&type=0&sub_region=34&root=1000034&prver=0&pronetvd=null&tvd=100100084849160'
    # url = 'http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=1000034&tvd=100100084849160&vrn=100100084849062&prver=0&pronetvd=null&region=0&sub_region=0&type=469&vibid=100100084849160'
    # url = 'http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1&tvd=100100084849066&vrn=100100084849062&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100084849066&type=469'
    data = get_soap_data(url)
    return soap_tree(data)


uiks = get_uiks_address()
# pprint(set(uiks.values()))
# pops = get_population()
# print(set(pops.keys()))
breakpoint()
