import pickle
import random
import re
from collections import defaultdict

from bs4 import BeautifulSoup
from redis import Redis

from app.settings import REDIS_HOST
from app.utils import _get


ROOT_URL = 'http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1&tvd=100100084849066&vrn=100100084849062&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100084849066&type=226'


def get_soap_data(url=''):
    data = _get(url).content.decode('cp1251')
    return BeautifulSoup(data, features="html.parser")


def get_elements(url):
    soap = get_soap_data(url)
    data = {}
    for option in soap.find_all('option'):
        if option.text == '---':
            continue
        data.update({option.text.strip(): option['value']})
    return data


def get_region_link(region):
    links = get_elements(ROOT_URL)
    return links[region]


def process_node(soap):
    for option in soap.find_all('option'):
        if option.text == '---':
            continue

        data = get_soap_data(option_replace(option['value']))
        next_page = find_next(data)
        if next_page == 'ok':
            process_node(data)
        elif not next_page:
            p_key = option.text[option.text.find('№')+1:]
            redis = Redis(host=REDIS_HOST)
            # TODO: добавить 10-40% рандомной в качестве детей
            redis.set(f'uik-population-{p_key}', get_result(data))
        else:
            process_node(get_soap_data(next_page))


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
    block_result = soap.find('td', text=re.compile(
        'Число избирателей, включенных в список избирателей'))
    result = 0
    if block_result:
        result = int(block_result.parent.find('b').text)
    for link in soap.find_all('a'):
        if link.text == 'Итоги голосования':
            page_result = get_soap_data(option_replace(link.get('href')))
            res = get_result(page_result)
            if res:
                result = res
    return result


def option_replace(value=''):
    return value.replace(';', '&')


def generate_people(peoples: int, places: int):
    if places < 1:
        return {i: 0 for i in range(places)}
    mid = int(round(peoples/places, 1))
    addrs = {i: mid for i in range(places)}
    buff = peoples - (places * mid)
    i = 0
    max_people = int(mid * 1.5)
    while buff:
        if max_people > addrs[i] > 4:
            diff = random.randint(0, max_people-addrs[i])
            if diff > buff:
                diff = buff
            buff -= diff
            addrs[i] += diff
        if addrs[i] > max_people:
            diff = addrs[i] - random.randint(max_people-2, max_people+4)
            if diff > buff:
                diff = buff
            buff += diff
            addrs[i] -= diff
        if addrs[i] < 2:
            diff = random.randint(0, mid+1)
            if diff > buff:
                diff = buff
            buff -= diff
            addrs[i] += diff

        i += 1
        if i > places-1:
            i = 0
    return addrs


def get_addresses(uikkey):
    redis = Redis(host=REDIS_HOST)
    redis_key = f'uik-addresses-{uikkey}'
    adresses = redis.lrange(redis_key, 0, redis.llen(redis_key))
    adresses = list(map(lambda x: pickle.loads(x), adresses))
    return adresses


def get_population(uikkey):
    redis = Redis(host=REDIS_HOST)
    redis_key = f'uik-population-{uikkey}'
    return int(redis.get(redis_key).decode('utf-8'))


def get_uik_data(uikkey):
    redis = Redis(host=REDIS_HOST)

    uik = pickle.loads(redis.get(f'uik-{uikkey}'))
    addresses = get_addresses(uikkey)
    houses = []
    i = 1
    generated = 0
    addrs = set()
    places = defaultdict(set)
    for address in addresses:
        components = address['components']
        addr = components.copy()
        place = '-'
        if '11' in components.keys():
            del addr['11']
            place = components['11']
        addr_str = ', '.join(addr.values())
        places[addr_str].add(place)
        addrs.add(addr_str)

    uik['places'] = sum([len(place) for place in places.values()])
    uik['people'] = get_population(uikkey)
    addrs_people = generate_people(uik['people'], uik['places'])
    last = 0
    for addr in addrs:
        place = ', '.join(sorted(places[addr]))

        addr_places = len(places[addr])
        people = sum([v for k, v in addrs_people.items() if last <= k < last + addr_places])
        last += addr_places
        generated += people
        # coords = ','.join(data['coords'])
        houses.append({'address': addr, 'place': place, 'people': people, 'i': i})

        i += 1
    uik['generated'] = generated
    uik['houses'] = houses
    return uik
