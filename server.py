import json
import os
import pickle
import random
from math import ceil

from flask import Flask, request, jsonify, render_template
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
    mid = ceil(uik['people'] / uik['places'])
    generated = 0
    all_people = uik['people']
    for addr,data in uik['houses'].items():
        people, all_people = generate_people(data['place'], mid, all_people)
        # print(people, all_people)
        generated += people
        place = ', '.join(data['place']) if len(data['place']) else '-'
        coords = ','.join(data['coords'])
        data.update({'address': ', '.join(addr), 'place': place,
                     'coords': coords, 'i': i, 'people': people})
        houses.append(data)
        i += 1
    uik['houses'] = houses
    uik['generated'] = generated
    # return jsonify(uik)
    return render_template('uik.html', uik=uik, uikkey=uikkey)


def generate_people(places, mid, all_people):
    if len(places):
        peoples = 0
        for place in places:
            inc_peoples, all_people1 = generate_people([], mid, all_people)
            peoples += inc_peoples
    else:
        iter = range(1, mid)
        weights = [.2*(2 if i%2 == 0 else 3) for i in range(len(iter))]
        peoples = random.choices(iter, weights=weights)[0]
        # import pdb
        # pdb.set_trace()
    if peoples > all_people:
        peoples = all_people
    # print(peoples, all_people)
    all_people -= peoples
    # print(all_people)
    # print('------')
    return peoples, all_people
