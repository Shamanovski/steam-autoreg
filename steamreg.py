import requests
import time
import string
import random
import sys
import re
import json
import logging
from websocket import create_connection
from proxybroker import Broker

from steampy.client import SteamClient
from steampy import guard

logger = logging.getLogger('__main__')


class SteamAuthError(Exception): pass
class SteamCaptchaError(Exception): pass
class RuCaptchaError(Exception): pass


class SteamRegger:

    def __init__(self, proxy=None):
        self.proxy = proxy

    @staticmethod
    def handle_request(session, url, data={}, timeout=30):
        while True:
            try:
                resp = session.post(url, data=data, timeout=timeout).json()
                return resp
            except requests.exceptions.Timeout as err:
                logger.error('%s %s', err, url)
            except json.decoder.JSONDecodeError as err:
                logger.error('%s %s', err, url)

    def mobile_login(self, login_name, password, email=None, email_passwd=None):
        steam_client = SteamClient(None, self.proxy)
        resp = steam_client.mobile_login(login_name, password, None, email, email_passwd)
        resp_message = resp.get('message', None)
        if resp_message:
            if 'Please verify your humanity' in resp_message:
                raise SteamCaptchaError('Too many unsuccessful attempts to log in. Steam demands to solve captcha')
            elif 'name or password that you have entered is incorrect' in resp_message:
                raise SteamAuthError('Incorrect login or password: ' + login_name)

        if resp['requires_twofactor']:
            raise SteamAuthError('Mobile Guard has already been set up: ' + login_name)

        if resp.get('emailauth_needed', None):
            raise SteamAuthError('Email Guard has been set up.')

        if not steam_client.oauth:
            error = 'Failed to log in: {}:{}'.format(
                        login_name, password)
            raise SteamAuthError(error)

        return steam_client

    def addphone_request(self, steam_client, phone_num):
        sessionid = steam_client.session.cookies.get(
                    'sessionid', domain='steamcommunity.com')
        data = {
            'op': 'add_phone_number',
            'arg': phone_num,
            'sessionid': sessionid
        }
        response = self.handle_request(steam_client.session,
                                       'https://steamcommunity.com/steamguard/phoneajax', data=data)
        logger.info(str(response))
        return response

    def is_phone_attached(self, steam_client):
        sessionid = steam_client.session.cookies.get(
                    'sessionid', domain='steamcommunity.com')
        data = {
            'op': 'has_phone',
            'arg': None,
            'sessionid': sessionid
        }
        while True:
            try:
                response = self.handle_request(steam_client.session,
                    'https://steamcommunity.com/steamguard/phoneajax', data=data)
                break
            except json.decoder.JSONDecodeError as err:
                logger.error(err)
                time.sleep(3)

        return response['has_phone']

    def checksms_request(self, steam_client, sms_code):
        sessionid = steam_client.session.cookies.get(
                    'sessionid', domain='steamcommunity.com')
        data = {
            'op': 'check_sms_code',
            'arg': sms_code,
            'sessionid': sessionid
        }
        response = self.handle_request(
            steam_client.session, 'https://steamcommunity.com/steamguard/phoneajax', data=data)
        logger.info(str(response))
        return response

    def add_authenticator_request(self, steam_client):
        device_id = guard.generate_device_id(steam_client.oauth['steamid'])
        while True:
            try:
                mobguard_data = self.handle_request(steam_client.session,
                    'https://api.steampowered.com/ITwoFactorService/AddAuthenticator/v0001/',
                    data = {
                        "access_token": steam_client.oauth['oauth_token'],
                        "steamid": steam_client.oauth['steamid'],
                        "authenticator_type": "1",
                        "device_identifier": device_id,
                        "sms_phone_id": "1"
                    })['response']
            except json.decoder.JSONDecodeError:
                time.sleep(3)
                continue
            logger.info(str(mobguard_data))
            if mobguard_data['status'] not in (1, 2):
                time.sleep(5)
                continue
            break

        mobguard_data['device_id'] = device_id
        mobguard_data['Session'] = {}
        mobguard_data['Session']['WebCookie'] = None
        for mafile_key, resp_key in (('SteamID', 'steamid'), ('OAuthToken', 'oauth_token')):
            mobguard_data['Session'][mafile_key] = steam_client.oauth[resp_key]

        for mafile_key, resp_key in (
                ('SessionID', 'sessionid'),
                ('SteamLogin', 'steamLogin'),
                ('SteamLoginSecure', 'steamLoginSecure')):
            mobguard_data['Session'][mafile_key] = steam_client.session.cookies[resp_key]

        return mobguard_data

    def finalize_authenticator_request(self, steam_client, mobguard_data, sms_code):
        one_time_code = guard.generate_one_time_code(mobguard_data['shared_secret'], int(time.time()))
        data= {
            "steamid": steam_client.oauth['steamid'],
            "activation_code": sms_code,
            "access_token": steam_client.oauth['oauth_token'],
            'authenticator_code': one_time_code,
            'authenticator_time': int(time.time())
        }
        while True:
            try:
                fin_resp = self.handle_request(steam_client.session,
                    'https://api.steampowered.com/ITwoFactorService/FinalizeAddAuthenticator/v0001/',
                    data=data)['response']
            except json.decoder.JSONDecodeError as err:
                logger.error("json error in the FinalizeAddAuthenticator request")
                time.sleep(3)
                continue
            logger.info(str(fin_resp))
            if (fin_resp.get('want_more') or fin_resp['status'] == 88):
                time.sleep(5)
                continue
            elif fin_resp['status'] == 2:
                fin_resp['success'] = True
            break

        return fin_resp['success']

    def make_account_unlimited(self, mobguard_data, wallet_code, get_api_key=False):
        steam_client = SteamClient()
        steam_client.login(mobguard_data['account_name'], mobguard_data['account_password'], mobguard_data)
        data = {
            'wallet_code': wallet_code,
            'CreateFromAddress': '1',
            'Address': 'Russia',
            'City': 'Russia',
            'Country': 'RU',
            'State': '',
            'PostCode': '0001'
        }
        steam_client.session.post('https://store.steampowered.com/account/validatewalletcode/',
                                  data={'wallet_code': wallet_code})
        steam_client.session.post('https://store.steampowered.com/account/createwalletandcheckfunds/',
                                  data=data)
        steam_client.session.post('https://store.steampowered.com/account/confirmredeemwalletcode/',
                                  data={'wallet_code': wallet_code})

        if get_api_key:
            sessionid = steam_client.session.cookies.get(
                        'sessionid', domain='steamcommunity.com')
            data = {
                'domain': 'domain.com',
                'agreeToTerms': 'agreed',
                'sessionid': sessionid,
                'Submit': 'Register'
            }
            time.sleep(10)
            r = steam_client.session.post('https://steamcommunity.com/dev/registerkey', data=data)
            key = re.search('Key: (.+)</p', r.text).group(1)
            return key

    def create_account_web(self, rucaptcha_api_key, thread_lock):

        def generate_captcha():
            gid = session.get('https://store.steampowered.com/join/refreshcaptcha/?count=1',
                               headers={'Host': 'store.steampowered.com'}, timeout=10).json()['gid']
            captcha_img = session.get('https://store.steampowered.com/public/captcha.php?gid={}'
                                      .format(gid), timeout=30).content
            resp = requests.post('http://rucaptcha.com/in.php',
                                 files={'file': ('captcha', captcha_img, 'image/png')},
                                 data={'key': rucaptcha_api_key},
                                 timeout=30)

            captcha_id = resp.text.partition('|')[2]
            return captcha_id, gid

        def send_captcha(captchagid, captcha_text, email):
            data = {
                'captchagid': captchagid,
                'captcha_text': captcha_text,
                'email': email,
                'count': '1'
            }
            resp = self.handle_request(session, 'https://store.steampowered.com/join/verifycaptcha',
                                       data=data)
            logger.info(resp)
            return resp

        def resolve_captcha(captcha_id, gid):
            while True:
                time.sleep(10)
                r = requests.post('http://rucaptcha.com/res.php?key={}&action=get&id={}'
                                  .format(rucaptcha_api_key, captcha_id), timeout=30)
                logger.info(r.text)
                if 'CAPCHA_NOT_READY' in r.text:
                    continue
                elif 'ERROR_CAPTCHA_UNSOLVABLE' in r.text:
                    return None
                break
            resolved_captcha = r.text.partition('|')[2].replace('amp;', '')
            return resolved_captcha

        session = requests.Session()
        if self.proxy:
            session.proxies.update(self.proxy)
        session.headers.update({'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36'),
                                'Accept-Language': 'q=0.8,en-US;q=0.6,en;q=0.4'})

        while True:
            captcha_id, gid = generate_captcha()
            captcha_text = resolve_captcha(captcha_id, gid)
            if not captcha_text:
                continue
            login_name = self.generate_login_name(session)
            password = self.generate_credential(2, 4)
            with thread_lock:
                email, ws = self.generate_mailbox()
            logger.info("Email box: %s", email)
            logger.info("Resolving captcha... %s", login_name)
            resp = send_captcha(gid, captcha_text, email)
            if not resp['bCaptchaMatches']:
                logger.info("Captcha text is wrong: %s", captcha_text)
                requests.post('http://rucaptcha.com/res.php?key={}&action=reportbad&id={}'
                              .format(rucaptcha_api_key, captcha_id), timeout=30)
            elif not resp['bEmailAvail']:
                logger.info("Email box is already used: %s", email)
            else:
                break

        logger.info("Confirming email... %s", login_name)
        with thread_lock:
            creationid = self.confirm_email(session, ws, login_name, gid, captcha_text, email)
        logger.info("Email confirmed: %s %s", email, login_name)

        data = {
            'accountname': login_name,
            'password': password,
            'email': email,
            'captchagid': gid,
            'captcha_text': captcha_text,
            'i_agree': '1',
            'ticket': '',
            'count': '32',
            'lt': '0',
            'creation_sessionid': creationid
        }
        resp = self.handle_request(session, 'https://store.steampowered.com/join/createaccount/',
                                   data=data, timeout=25)
        logger.info('create account response: %s', resp)

        return login_name, password, email

    def generate_mailbox(self):
        ssl_option = {"check_hostname": False, "cert_reqs": 0, "ca_certs": "cacert.pem"}
        ws = create_connection('wss://dropmail.me/websocket', sslopt=ssl_option)
        mailbox = ws.recv().partition(':')[0].lstrip('A')
        ws.recv()  # skip the message with domains
        return mailbox, ws

    def confirm_email(self, session, websocket, login_name, gid, captcha_text, email):
        data = {
            'accountname': login_name,
            'captcha_text': captcha_text,
            'captchagid': gid,
            'email': email
        }
        resp = self.handle_request(session, 'https://store.steampowered.com/join/ajaxverifyemail', data=data)
        logger.info('ajaxverify response: %s', resp)
        creationid = resp['sessionid']
        response = websocket.recv()
        websocket.close()
        try:
            mail = json.loads(response.lstrip('I'))['text']
        except Exception as err:
            logger.error('Error: %ss\nResponse: %s\nMailbox: %s', err, response, email)
            sys.exit(1)

        link = re.search(r'(https:\/\/.+newaccountverification.+?)\n', mail).group(1)
        session.get(link)
        return creationid

    def generate_login_name(self, session):
        while True:
            login_name = self.generate_credential(2, 4, uppercase=False)
            r = self.handle_request(session, 'https://store.steampowered.com/join/checkavail',
                                    data={'accountname': login_name, 'count': 1})
            logger.info(str(r) + " %s", login_name)
            if r['bAvailable']:
                return login_name
            time.sleep(3)

    @staticmethod
    def generate_credential(start, end, uppercase=True):
        char_sets = [string.ascii_lowercase, string.digits, string.ascii_uppercase]
        random.shuffle(char_sets)
        func = lambda x: ''.join((random.choice(x) for _ in range(random.randint(start, end))))
        credential = ''.join(map(func, char_sets))
        if not uppercase:
            credential = credential.lower()
        return credential

    @staticmethod
    def activate_account(steam_client):
        url = 'https://steamcommunity.com/profiles/{}/edit'.format(steam_client.steamid)
        data = {
            'sessionID': steam_client.get_session_id(),
            'type': 'profileSave',
            'personaName': steam_client.login_name,
            'summary': 'No information given.',
            'primary_group_steamid': '0'
        }
        steam_client.session.post(url, data=data, timeout=30)

    @staticmethod
    def remove_intentory_privacy(steam_client):
        url = 'http://steamcommunity.com/profiles/{}/edit/settings'.format(steam_client.steamid)
        data = {
            'sessionID': steam_client.get_session_id(),
            'type': 'profileSettings',
            'privacySetting': '3',
            'commentSetting': 'commentanyone',
            'inventoryPrivacySetting': '3',
            'inventoryGiftPrivacy': '1',
        }
        steam_client.session.post(url, data=data, timeout=30)

    @staticmethod
    def fetch_tradeoffer_link(steam_client):
        url = 'http://steamcommunity.com/profiles/%s/tradeoffers/privacy' % steam_client.steamid
        resp = steam_client.session.get(url, timeout=30)
        regexr = 'https:\/\/steamcommunity.com\/tradeoffer\/new\/\?partner=.+&token=.+(?=" )'
        try:
            return re.search(regexr, resp.text).group()
        except AttributeError as err:
            logger.error("Failed to fetch offer link %s", err)
            return ''


if __name__ == '__main__':
    import logging

    logging.getLogger("requests").setLevel(logging.ERROR)
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler = logging.FileHandler('database/logs.txt', 'w', encoding='utf-8')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    foo = SteamRegger()
    foo.create_accounts_client("1")
