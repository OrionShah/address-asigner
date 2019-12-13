"""Точки входа для веба."""

from flask import Flask, jsonify, redirect, render_template, request
from redis import Redis

from app import tasks, utils
from app.address import get_children, prepare_parents
from app.population import get_region_link, get_uik_data
from app.settings import REDIS_HOST

app = Flask(__name__)
app.debug = True


@app.route('/process', defaults={'service_id': None}, methods=['GET'])
@app.route('/process/<service_id>', methods=['GET'])
def children(service_id: str):
    services = service_id.split('-') if service_id else [None]
    debug = False
    if 'debug' in request.args.keys():
        debug = request.args['debug'] == '1'
    return render_template('process_list.html',
                           children=get_children(services[-1], service_id),
                           service_id=service_id, debug=debug)


@app.route('/process/<service_id>', methods=['POST'])
def start_process(service_id):
    services = service_id.split('-')
    parents = prepare_parents(services)

    tasks.process_node.delay(services[-1], parents)
    tasks.process_population.delay(get_region_link(parents[2]))

    url = '-'.join(services[0:-1])
    return redirect(f'/process/{url}', code=302)


@app.route('/test')
def test():
    redis = Redis(host=REDIS_HOST)
    keys = []
    for addr_key in redis.keys('address-*'):
        keys.append(addr_key.decode('utf-8'))
        # redis.delete(addr_key)
    return jsonify({'1len': len(keys), 'keys': keys[:10]})
    # data = redis.lrange('uik-addresses-733', 0,
    #                     redis.llen('uik-addresses-733'))
    # data = redis.lrange('uik-addresses-733', 0, 10)
    # data = pickle.loads(redis.get('uik-addresses-733'))
    # return jsonify([pickle.loads(el) for el in data])


@app.route('/')
def index():
    redis = Redis(host=REDIS_HOST)
    uiks = [key.decode('utf-8') for key in redis.keys('uik-*')]
    uiks = filter(lambda x: 'address' not in x, uiks)
    uiks = filter(lambda x: 'population' not in x, uiks)
    uiks = list(map(lambda x: int(x.replace('uik-', '')), uiks))
    return render_template('index.html', uiks=sorted(uiks))


@app.route('/<uikkey>')
def uik(uikkey):
    uik = get_uik_data(uikkey)
    return render_template('uik.html', uik=uik, uikkey=uikkey)


@app.route('/<uikkey>', methods=['POST'])
def process_uik(uikkey):
    tasks.process_uik.delay(uikkey)
    return redirect(f'/{uikkey}')


@app.route('/map')
def map():
    return render_template('debug.html')
