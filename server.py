"""Точки входа для веба."""
import pickle
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, send_file
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
    tasks.process_uik(uikkey)
    return redirect(f'/{uikkey}')


@app.route('/map')
def map_debug():
    return render_template('debug.html')


def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = (str(callback) + '(' + str(f()) + ')').replace('\'', '\"')
            return app.response_class(content, mimetype='application/json')
        else:
            return f(*args, **kwargs)
    return decorated_function


@app.route('/datalayer/')
@support_jsonp
def datalayer():
    tile_x = int(request.args['x'])
    tile_y = int(request.args['y'])
    zoom = int(request.args['z'])

    redis = Redis(host=REDIS_HOST)
    addrs = redis.keys(f'map-address-{zoom}-*')
    resp = []

    features = []
    for addr in addrs:
        addr = addr.decode('utf-8')
        addr_components = addr.split('-')
        # in_x = tile_x <= int(addr_components[3]) <= (tile_x + 256)
        # in_y = tile_y <= int(addr_components[4]) <= (tile_y + 256)
        in_x = tile_x == int(addr_components[3])
        in_y = tile_y == int(addr_components[4])
        if in_x and in_y:
            resp.append(addr)
            house = pickle.loads(redis.get(addr))
            point = {
                "type": "Feature",
                "properties": {
                    # "balloonContentBody": f"Жителей: {house['people']}",
                    # "balloonContentHeader": house['address'],
                    "balloonContent": f"Жителей: {house['people']}",

                    "id": addr_components[3] + addr_components[4] + str(random.randint(1, 100000)),
                    # "id": 1,
                    "HotspotMetaData": {
                        "RenderedGeometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [93, 137], [105, 108], [132, 103],
                                    [153, 117], [162, 142],
                                    [146, 162], [114, 162], [93, 137]
                                ]
                            ]
                            # "type": "Polygon",
                            # "coordinates": [
                            #     [[0, 0], [10, 10], [10, 0], [0, 10]],
                            #     [[0, 0], [10, 10], [10, 0], [0, 10]],
                            # ]
                        }
                    }
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [house['coords']['lat'], house['coords']['lon']],
                },
                # "options": {
                #     "preset": "islands#yellowIcon"
                # }
            }
            features.append(point)

    points = {"data": {"type": "FeatureCollection", "features": features}}
    # return f'{callback}({json.dumps(points)})'
    return points


@app.route('/hotspot_layer/images/<zoom>/<img>.png')
def img(zoom, img):
    return send_file('tile.png')
