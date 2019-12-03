import pickle
import random

from flask import Flask, render_template
from redis import Redis

app = Flask(__name__)
app.debug = True


@app.route('/')
def index():
    # redis = Redis(host='redis')
    redis = Redis()
    uiks = [key.decode('utf-8') for key in redis.keys('uik-*')]
    return render_template('index.html', uiks=uiks)


@app.route('/<uikkey>')
def uik(uikkey):
    # redis = Redis(host='redis')
    redis = Redis()

    uik = pickle.loads(redis.get(uikkey))
    houses = []
    i = 1
    generated = 0
    addrs = generate_people(uik['people'], uik['places'])
    last = 0
    for addr, data in uik['houses'].items():
        place = ', '.join(data['place']) if len(data['place']) else '-'
        coords = ','.join(data['coords'])

        places = len(data['place']) if len(data['place']) else 1
        people = sum([v for k,v in addrs.items() if last <= k < last+places])
        last += places
        generated += people

        data.update({'address': ', '.join(addr), 'place': place,
                     'coords': coords, 'i': i, 'people': people})
        houses.append(data)
        i += 1
    uik['houses'] = houses
    uik['generated'] = generated
    return render_template('uik.html', uik=uik, uikkey=uikkey)


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
