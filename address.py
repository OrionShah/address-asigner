import re

import requests
from pprint import pprint
from bs4 import BeautifulSoup

LIMITS = 4

class Address:
    def get_addresses_by_coords(self):
        pass


def get_data(url, id=''):
    content = requests.get(f'{url}{id}')
    return content.json()


def get_uik(value):
    result = {}
    for key, val in value.items():
        response = requests.get(f'http://www.cikrf.ru/services/lk_address/{val}?do=result').content.decode('CP1251')
        substr = 'Номер Территориальной избирательной комиссии: '
        start = response.find(substr)
        if start == -1:
            continue
        end = response[start:].find('<')
        uik = response[start+len(substr):start+end]
        result.update({key: int(uik)})
    return result


def tree(values, key, deep):
    result = {}
    i = 0
    for value in values:
        response = get_data('http://www.cikrf.ru/services/lk_tree/?id=', value['id'])
        if len(response):
            result.update(tree(response, f'{key} {value["text"]}', deep+1))
        else:
            result.update({f'{key} {value["text"]}': value['a_attr']['intid']})
        i += 1
        if i > LIMITS:
            break
    return result


def get_uiks_address():
    data = get_data('http://www.cikrf.ru/services/lk_tree/?', 'first=1&id=%23')
    data = [data[0]['children'][37]]
    # data = data[0]['children'][0]
    res = tree(data, 'Россия', 0)
    # pprint(res)
    return get_uik(res)


def option_replace(value=''):
    return value.replace(';', '&')


def get_soap_data(url=''):
    data = requests.get(url).content.decode('cp1251')
    return BeautifulSoup(data, features="html.parser")


def find_next(soap):
    if len(soap.find_all('option')):
        return 'ok'

    for link in soap.find_all('a'):
        if link.text == 'сайт избирательной комиссии субъекта Российской Федерации':
            return option_replace(link['href'])
    return None


def get_result(soap):
    for link in soap.find_all('a'):
        if link.text == 'Итоги голосования':
            page_result = get_soap_data(option_replace(link.get('href')))
            result = page_result.find('td', text=re.compile(
                'Число избирателей, включенных в список избирателей')).parent.find(
                'b').text
            return result


def soap_tree(soap):
    result = {}
    i = 0
    for option in soap.find_all('option'):
        if option.text == '---':
            continue

        data = get_soap_data(option_replace(option['value']))
        next = find_next(data)
        if next == 'ok':
            result.update(soap_tree(data))
        elif not next:
            key = option.text[option.text.find('№')+1:]
            result.update({int(key): get_result(data)})
        else:
            result = soap_tree(get_soap_data(next))
        i += 1
        if i > LIMITS:
            break
    return result


def get_population():
    # url = 'http://www.vybory.izbirkom.ru/region/izbirkom?action=show&global=true&root=1000034&tvd=100100084849160&vrn=100100084849062&prver=0&pronetvd=null&region=0&sub_region=0&type=469&vibid=100100084849160'
    url = 'http://www.vybory.izbirkom.ru/region/region/izbirkom?action=show&root=1&tvd=100100084849066&vrn=100100084849062&region=0&global=true&sub_region=0&prver=0&pronetvd=null&vibid=100100084849066&type=469'
    data = get_soap_data(url)
    return soap_tree(data)


uiks = get_uiks_address()
pops = get_population()
print(set(uiks.values()), set(pops.keys()))
breakpoint()
