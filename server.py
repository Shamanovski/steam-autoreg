import json
import logging
import logging.handlers
import shelve
import datetime
import traceback
import uuid
import hashlib

import requests
from flask import Flask, request, render_template, jsonify

# disable flask and requests info logs
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

logger = logging.getLogger()
logger.setLevel(level=logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(
    'logs.txt', maxBytes=10 * 1024 * 1024, backupCount=1, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def check_license_autoreg():
    logger.info('Application: autoreg')
    success = False
    data = {key: value for key, value in request.form.items()}
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    try:
        key = data['key']
    except KeyError:
        return success
    db = shelve.open("clients")
    db_data = {}
    try:
        if key in db:
            db_data = db[key]
            success = True
        else:
            logger.info('WRONG KEY: %s, %s\n', data, ip)
    finally:
        db.close()

    return jsonify({"success_x001": success, "data": db_data}), 200


@app.route('/check_license', methods=['POST'])
def check_license_farmtools():
    with open('farmtools_keys.txt', 'r') as f:
        farmtools_keys = [i.rstrip() for i in f.readlines()]

    logger.info('Application: farmtools')
    success = False
    data = {key: value for key, value in request.form.items()}
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    try:
        key = data['key']
    except KeyError:
        return success
    db = shelve.open('farmtools')
    try:
        if key in farmtools_keys:
            if not db.get(key, None):
                data['ip'] = (ip, get_city_from_ip(ip))
                logger.info('IP : %s', ip)
                update_database(data, db, key)
                success = True
            else:
                db_data = db[key]
                success = check_device(data, db_data, ip)
        else:
            logger.info('WRONG KEY: %s, %s\n', data, ip)
    finally:
        db.close()

    return jsonify({'success': success}), 200


@app.route('/showdb', methods=['GET'])
def show_db():
    with shelve.open('farmtools_db') as db:
        try:
            return render_template('farmtools_db.html', database=dict(db)), 200
        except:
            logger.error(traceback.print_exc())


@app.route('/catalogue', methods=['GET'])
def get_catalogue():
    key, uid, catalogue_key = request.headers['key'], request.headers['uid'], request.headers['catalogue-key']
    with shelve.open('farmtools_db') as db:
        try:
            client_data = db[key]
        except KeyError:
            logger.error("Client is not in the database: %s %s", key, uid)
            return 'Not allowed', 403

    if client_data['uid'] != uid:
        logger.error("UID is different: %s %s", uid, client_data)
        return 'Not allowed. Wrong UID.', 403

    is_valid = check_catalogue_key(catalogue_key)
    if not is_valid:
        logger.info("Catalogue key is not valid: %s %s", catalogue_key, client_data)
        return 'Not allowed. The catalogue key was not provided or it expired.', 403

    logger.info("Successfully returned catalogue: %s", client_data)
    with open("catalogue.json", 'r', encoding='utf-8') as f:
        return f.read(), 200


@app.route('/generate-product-key')
def generate_product_key():
    login = request.args.get("login")
    if login is not None:
        login = login.strip()

    with shelve.open("clients") as db:
        for data in db.values():
            if login == data.get("login", None):
                return "Already used", 406
        product_key = str(uuid.uuid4())
        db[product_key] = {"login": login, "registration_quota": 0, "binding_quota": 0, "payments": {}}

    return product_key, 200


@app.route('/addquota', methods=['POST'])
def add_quota():
    data = {key: value for key, value in request.form.items()}
    key, registration_quota, binding_quota = data["key"], data["registration_quota"], data["binding_quota"]
    with shelve.open("clients", writeback=True) as db:
        client = db[key]
        try:
            client["registration_quota"] += int(registration_quota)
            client["binding_quota"] += int(binding_quota)
        except KeyError:
            client["registration_quota"] = int(registration_quota)
            client["binding_quota"] = int(binding_quota)
            client["payments"] = {}
    return "OK", 200


@app.route('/updatequota', methods=['POST'])
def update_quota():
    data = {key: value for key, value in request.form.items()}
    key, registration_quota, binding_quota = data["key"], data["registration_quota"], data["binding_quota"]
    with shelve.open("clients", writeback=True) as db:
        client = db[key]
        client["registration_quota"] = int(registration_quota)
        client["binding_quota"] = int(binding_quota)
    return "OK", 200


@app.route('/validatecode')
def validate_code():
    code = request.args.get("uniquecode")
    key = request.args.get("key")
    if key is not None:
        key = key.strip()
    success = False
    try:
        db = shelve.open("clients", writeback=True)
        try:
            client = db[key]
        except KeyError:
            message = "Не удалось найти ключ продукта программы в базе данных"
            return jsonify({"success": success, "message": message}), 200

        try:
            used_codes = db["used_codes"]
        except KeyError:
            used_codes = db["used_codes"] = set()
        if code in used_codes:
            message = "Этот код уже активирован"
            return jsonify({"success": success, "message": message}), 200
        resp = requests.post("https://www.oplata.info/xml/check_unique_code.asp", data=json.dumps({
            "id_seller": 479531,
            "unique_code": code,
            "sign": hashlib.md5("479531:{code}:C9149CDFDC".format(code=code).encode("utf-8")).hexdigest()
        }), headers={"Content-Type": "application/json"}).json()
        if resp["retval"] == "-2":
            message = "Неверно введен код"
            return jsonify({"success": success, "message": message}), 200

        id_goods = resp["id_goods"]
        if id_goods == "2542451":
            quota = "registration_quota"
        elif id_goods == "2550416":
            quota = "binding_quota"
        amount = int(resp["cnt_goods"])
        client[quota] += amount
        try:
            client["payments"][resp["inv"]] = resp
        except KeyError:
            client["payments"] = {}
            client["payments"][resp["inv"]] = resp
        used_codes.add(code)
    finally:
        db.close()
    success = True
    message = "Код успешно активирован. Перезапустите программу чтобы изменения вступили в силу"
    return jsonify({"success": success, "message": message, "amount": amount, "quota": quota}), 200


@app.route('/searchdb')
def search_database():
    method, value = request.args.get("method"), request.args.get("value")
    response = None
    with shelve.open("clients") as clients:
        if method == "login":
            for key, data in clients.items():
                if data.get("login", None) == value:
                    response = data.update({"key": key})
                    break
        elif method == "paymentid":
            for key, data in clients.items():
                for paymentid in data["payments"]:
                    if paymentid == value:
                        response = data.update({"key": key})
                        break
        elif method == "key":
            response = clients[value]

    return jsonify(response), 200


def check_catalogue_key(catalogue_key):
    expire_date = requests.get('http://steamkeys.ovh/get_time.php?key=%s' % catalogue_key).text
    if not expire_date:
        return False
    datetime_obj = datetime.datetime.strptime(expire_date, '%Y-%m-%d')
    if datetime.datetime.now() > datetime_obj:
        return False

    return True


def get_city_from_ip(ip_address):
    try:
        resp = requests.get('http://ip-api.com/json/%s' % ip_address).json()
    except requests.exceptions.ProxyError:
        return 'Unknown'
    return resp['city']


def update_database(data, db, key):
    db[key] = data
    logger.info('VALID KEY. Added to the database: %s\n', data)


def check_device(data, db_data, ip):
    if data['uid'] != db_data['uid']:
        logger.warning('UID is different (%s). The request has been declined: %s\n', data['uid'], db_data)
        return False

    stored_ip, stored_city = db_data['ip']
    if ip != stored_ip:
        city = get_city_from_ip(ip)
        if city != stored_city:
            logger.warning('The ip and the city are different (%s, %s). '
                'Data from database: %s', ip, city, db_data)
        logger.warning('IPs are different: %s-%s', ip, stored_ip)

    logger.info('The device has been authorized successfully: %s\n', db_data)
    return True
