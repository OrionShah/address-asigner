import pickle
import random
import re

from bs4 import BeautifulSoup
from redis import Redis

from app.settings import REDIS_HOST
from app.utils import _get


ROOT_URL = 'http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1&tvd=100100084849066&vrn=100100084849062&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100084849066&type=469'


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
    if not soap.find_all('option'):
        pass

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
            redis.set(f'uik-population-{p_key}', get_result(data))
            # result.update({int(p_key): pops})
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

def get_uik_data(uikkey):
    redis = Redis(host=REDIS_HOST)

    uik = pickle.loads(redis.get(f'uik-{uikkey}'))
    adresses = get_addresses(uikkey)
    houses = []
    i = 1
    generated = 0
    # addrs = generate_people(uik['people'], uik['places'])
    # last = 0
    # for addr, data in uik['houses'].items():
    #     place = ', '.join(data['place']) if len(data['place']) else '-'
    #     coords = ','.join(data['coords'])
    #
    #     places = len(data['place']) if len(data['place']) else 1
    #     people = sum(
    #         [v for k, v in addrs.items() if last <= k < last + places])
    #     last += places
    #     generated += people
    #
    #     data.update({'address': ', '.join(addr), 'place': place,
    #                  'coords': coords, 'i': i, 'people': people})
    #     houses.append(data)
    #     i += 1
    # uik['houses'] = houses
    # uik['generated'] = generated
    return uik
