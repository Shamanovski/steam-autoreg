from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showwarning
import sys
import datetime
import uuid
import os
import traceback
import threading

from sms_services import *
from steamreg import *


def uncaught_exceptions_handler(type, value, tb):
    logger.critical("Uncaught exception: {0} {1}\n{2}".format(type, value, ''.join(traceback.format_tb(tb))))


logger = logging.getLogger('__main__')

for dir_name in ('new_accounts', 'loaded_accounts'):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

if not os.path.exists('database/userdata.txt'):
    with open('database/userdata.txt', 'w') as f:
        f.write('{}')

sys.excepthook = uncaught_exceptions_handler
steamreg = SteamRegger()
with open("database/interface_states.json", "r") as f:
    STATES = json.load(f)


class MainWindow:

    def __init__(self, parent):
        self.parent = parent
        self.frame = Frame(self.parent)
        with open('database/userdata.txt', 'r') as f:
            self.userdata = json.load(f)

        success = self.authorize_user()
        if not success:
            self.deploy_activation_widgets(self.frame)
            return

        self.manifest_path = ''
        self.accounts_path = ''
        self.email_boxes_path = ''
        self.email_boxes_data = None
        self.proxy_path = ''
        self.proxy_data = []
        self.manifest_data = None
        self.old_accounts = None
        self.autoreg = IntVar()
        self.import_mafile = IntVar()
        self.mobile_bind = IntVar()
        self.fold_accounts = IntVar()
        self.onlinesim_api_key = StringVar()
        self.rucaptcha_api_key = StringVar()
        self.new_accounts_amount = IntVar()
        self.accounts_per_number = IntVar()
        self.temp_mail = IntVar()
        self.proxy_bool = IntVar()
        self.private_email_boxes = IntVar()
        self.email_domain = StringVar()
        self.status_bar = StringVar()
        self.country_code = StringVar()
        self.country_code.set('7')

        self.menubar = Menu(parent)
        parent['menu'] = self.menubar

        self.accounts_per_number_label = Label(self.frame, text='Amount of accounts per phone number')
        self.accounts_per_number_entry = Entry(self.frame, textvariable=self.accounts_per_number,
                                               width=2, disabledforeground='#808080')
        self.onlinesim_apikey_label = Label(self.frame, text='onlinesim api key:')
        self.onlinesim_apikey_entry = Entry(self.frame, textvariable=self.onlinesim_api_key, disabledforeground='#808080')

        self.new_accounts_amount_label = Label(self.frame, text='Amount of accounts for registration:')
        self.new_accounts_amount_entry = Entry(self.frame, textvariable=self.new_accounts_amount, width=4, disabledforeground='#808080')
        self.rucaptcha_apikey_label = Label(self.frame, text='rucaptcha api key:')
        self.rucaptcha_apikey_entry = Entry(self.frame, textvariable=self.rucaptcha_api_key, disabledforeground='#808080')

        self.country_code_label = Label(self.frame, text='Country of a phone number:')
        self.russia_option = Radiobutton(self.frame, text="Russia", variable=self.country_code, value="7")
        self.china_option = Radiobutton(self.frame, text="China", variable=self.country_code, value="86")

        tools_frame = Frame(self.parent)
        self.tools_label = Label(tools_frame, text='Tools:')
        self.options_label = Label(tools_frame, text='Options:')
        self.autoreg_checkbutton = Checkbutton(tools_frame, text='Create new accounts',
                                               variable=self.autoreg, command=self.set_states,
                                               disabledforeground='#808080')
        self.temp_mail_checkbutton = Checkbutton(tools_frame, text='Use temporary email boxes',
                                                 variable=self.temp_mail, command=self.set_states,
                                                 disabledforeground='#808080')

        self.proxy_checkbutton = Checkbutton(tools_frame, text='Search public proxy list',
                                             variable=self.proxy_bool, command=self.set_states,
                                             disabledforeground='#808080')

        self.mafile_checkbutton = Checkbutton(tools_frame, text='Import maFile into SDA',
                                              variable=self.import_mafile, command=self.set_states,
                                              disabledforeground='#808080')
        self.mobile_bind_checkbutton = Checkbutton(tools_frame, text='Set up mobile guard',
                                                   variable=self.mobile_bind, command=self.set_states,
                                                   disabledforeground='#808080')
        self.fold_accounts_checkbutton = Checkbutton(tools_frame, text='Stock items at folders',
                                                     variable=self.fold_accounts, disabledforeground='#808080')

        self.start_button = Button(tools_frame, text='Start', command=self.start_process,
                                   bg='#CEC8C8', relief=GROOVE, width=50)
        tools_frame.grid(row=1, column=0, pady=5)

        log_frame = Frame(self.parent)
        self.log_label = Label(log_frame, text='Logs:')
        self.scrollbar = Scrollbar(log_frame, orient=VERTICAL)
        self.log_box = Listbox(log_frame, yscrollcommand=self.scrollbar.set)
        self.log_box.bind('<Enter>', self.freeze_log)
        self.log_box.bind('<Leave>', self.unfreeze_log)
        self.log_frozen = False
        self.scrollbar["command"] = self.log_box.yview
        self.scrollbar.bind('<Enter>', self.freeze_log)
        self.scrollbar.bind('<Leave>', self.unfreeze_log)

        self.frame.grid(row=0, column=0, sticky=W)
        log_frame.columnconfigure(0, weight=999)
        log_frame.columnconfigure(1, weight=1)
        log_frame.grid(row=2, column=0, sticky=NSEW)

        self.status_bar_label = Label(log_frame, anchor=W, text='Ready...', textvariable=self.status_bar)
        self.caption_label = Label(log_frame, text='by Shamanovsky')

        if self.userdata:
            self.set_attributes()

        self.pack_widgets()

    def set_states(self):
        for checkbutton_name, configs in sorted(STATES.items(), key=lambda item: item[1]["priority"]):
            flag = self.__getattribute__(checkbutton_name).get()
            for entry, state in configs.get("entries", {}).items():
                state = self.adjust_state(flag, state)
                self.__getattribute__(entry).configure(state=state)
            for menu_item, states in configs.get("menubar", {}).items():
                for menu_index, state in states.items():
                    state = self.adjust_state(flag, state)
                    self.__getattribute__(menu_item).entryconfig(menu_index, state=state)
            for checkbutton_attr, state in configs.get("checkbuttons", {}).items():
                state = self.adjust_state(flag, state)
                self.__getattribute__(checkbutton_attr).configure(state=state)

    @staticmethod
    def adjust_state(flag, state):
        reversed_states = {NORMAL: DISABLED, DISABLED: NORMAL}
        if not flag:
            state = reversed_states[state]
        return state

    def set_attributes(self):
        for attr_name, value in self.userdata.items():
            if attr_name == 'manifest_path':
                self.load_manifest(value)
            else:
                attribute = self.__getattribute__(attr_name)
                attribute.set(value)

    def pack_widgets(self):
        self.load_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Load...", menu=self.load_menu)
        self.load_menu.add_command(label="Own accounts", command=self.accounts_open)
        self.load_menu.add_command(label="Own emails", command=self.email_boxes_open)
        self.load_menu.add_command(label="Own proxy list", command=self.proxy_open)
        self.load_menu.add_command(label="SDA Manifest", command=self.manifest_open)

        self.onlinesim_apikey_label.grid(row=0, column=0, pady=5, sticky=W)
        self.onlinesim_apikey_entry.grid(row=0, column=1, pady=5, padx=5, sticky=W)

        self.rucaptcha_apikey_label.grid(row=1, column=0, pady=5, sticky=W)
        self.rucaptcha_apikey_entry.grid(row=1, column=1, pady=5, padx=5, sticky=W)

        self.new_accounts_amount_label.grid(row=2, column=0, pady=5, sticky=W)
        self.new_accounts_amount_entry.grid(row=2, column=1, pady=5, padx=5, sticky=W)

        self.accounts_per_number_label.grid(row=3, column=0, pady=5, sticky=W)
        self.accounts_per_number_entry.grid(row=3, column=1, pady=5, padx=5, sticky=W)

        self.country_code_label.grid(row=4, column=0, pady=3, sticky=W)
        self.russia_option.grid(row=5, column=0, pady=3, sticky=W)
        self.china_option.grid(row=5, column=0, pady=3, sticky=E)

        self.tools_label.grid(row=0, column=0, pady=3, sticky=W)
        self.options_label.grid(row=2, column=0, pady=3, sticky=W)

        self.autoreg_checkbutton.grid(row=1, column=0, sticky=W)
        self.temp_mail_checkbutton.grid(row=3, column=0, pady=1, sticky=W)
        self.proxy_checkbutton.grid(row=4, column=0, pady=1, sticky=W)

        self.mobile_bind_checkbutton.grid(row=1, column=1, pady=1, sticky=W)
        self.mafile_checkbutton.grid(row=3, column=1, pady=1, sticky=W)
        self.fold_accounts_checkbutton.grid(row=4, column=1, pady=1, sticky=W)

        self.start_button.grid(row=5, pady=10, columnspan=2)
        self.log_label.grid(row=0, column=0, pady=5, sticky=W)
        self.log_box.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)
        self.status_bar_label.grid(row=2, column=0, columnspan=2, sticky=W, pady=5)
        self.caption_label.grid(row=2, column=0, sticky=E)
        self.set_states()

    def add_log(self, message):
        self.log_box.insert(END, message)
        if not self.log_frozen:
            self.log_box.yview(END)

    def freeze_log(self, *ignore):
        self.log_frozen = True

    def unfreeze_log(self, *ignore):
        self.log_frozen = False

    def run_process(self):
        if not self.check_input():
            return
        self.save_input()
        try:
            if self.mobile_bind.get():
                self.registrate_with_binding()
            elif self.autoreg.get():
                self.registrate_without_binding()
        except (OnlineSimError, RuCaptchaError) as err:
            showwarning(err.__class__.__name__, err,
                        parent=self.parent)
            logger.critical(err)
        except Exception:
            error = traceback.format_exc()
            showwarning("Internal error", error)
            logger.critical(error)

        self.status_bar.set('Готов...')

    def check_input(self):
        if not self.manifest_path and self.import_mafile.get():
            showwarning("Error", "The path to the SDA manifest is not specified",
                        parent=self.parent)
            return False

        if self.autoreg.get():
            try:
                self.check_rucaptcha_key()
            except RuCaptchaError as err:
                showwarning("Rucaptcha Error", err, parent=self.parent)
                return False
            try:
                if self.new_accounts_amount.get() <= 0:
                    raise ValueError
            except (TclError, ValueError):
                showwarning("Error", "The amount of accounts for registration is not specified",
                            parent=self.parent)
                return False

        if self.mobile_bind.get():
            try:
                if not 0 < self.accounts_per_number.get() <= 30:
                    raise ValueError
            except (TclError, ValueError):
                showwarning("Ошибка", "Specify amount of accounts per phone number less than 30 and more than 0",
                            parent=self.parent)
                return False
        return True

    def save_input(self):
        for field, value in self.__dict__.items():
            if field in ('status_bar', 'license'):
                continue
            if issubclass(value.__class__, Variable) or 'manifest_path' in field:
                try:
                    value = value.get()
                except AttributeError:
                    pass
                self.userdata[field] = value

    def registrate_without_binding(self):
        new_accounts_amount = self.new_accounts_amount.get()
        self.init_threads(new_accounts_amount)

    def registrate_with_binding(self):
        onlinesim_api_key = self.onlinesim_api_key.get()
        if not onlinesim_api_key:
            showwarning("Error", "API key for onlinesim.ru is not specified", parent=self.parent)
            return

        if not self.accounts_path and not self.autoreg.get():
            showwarning("Error", "The path to the text file with accounts data is not specified. "
                                 "If you don't have your own accounts, check 'Create new accounts'",
                        parent=self.parent)
            return

        accounts = self.new_accounts_generator() if self.autoreg.get() else self.old_account_generator()
        sms_service = OnlineSimApi(onlinesim_api_key)
        binder = Binder(self, sms_service)
        for accounts_package in accounts:
            binder.bind_accounts(accounts_package)

    def new_accounts_generator(self):
        ctr = 0
        new_accounts_amount = self.new_accounts_amount.get()
        accounts_per_number = self.accounts_per_number.get()
        while ctr < new_accounts_amount:
            remainder = new_accounts_amount - ctr
            if remainder < accounts_per_number:
                accounts_per_number = remainder
            new_accounts = self.init_threads(accounts_per_number, threads_amount=accounts_per_number)
            ctr += accounts_per_number
            yield new_accounts

    def init_threads(self, accs_amount, threads_amount=20):
        if threads_amount > 20:
            threads_amount = 20
        self.status_bar.set('Creating accounts, solving captchas...')
        threads = []
        new_accounts = []
        for _ in range(threads_amount):
            t = RegistrationThread(self, accs_amount, new_accounts)
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
            if thread.error:
                error_origin, error_text = thread.error
                showwarning("Error %s" % error_origin, error_text)
                return
        RegistrationThread.counter = 0
        return new_accounts

    def authorize_user(self):
        if os.path.exists('database/key.txt'):
            with open('database/key.txt', 'r') as f:
                user_data = json.load(f)
            resp = requests.post('https://shamanovski.pythonanywhere.com/',
                                 data={
                                         'login': user_data['login'],
                                         'key': user_data['key'],
                                         'uid': self.get_node()
                                 }).json()
        else:
            return False

        return resp['success']

    def check_license(self, frame):
        key, login = self.license_key_entry.get(), ''
        if not all((key, login)):
            showwarning('Error', 'Fill in all the fields')
            return
        resp = requests.post('https://shamanovski.pythonanywhere.com/',
                             data={
                                     'login': login,
                                     'key': key,
                                     'uid': self.get_node()
                             }).json()
        if not resp['success']:  # resp['success_x3tre43']:
            showwarning('Error', 'Wrong key or attempt to launch from unauthorized device')
            return

        with open('database/key.txt', 'w') as f:
            json.dump({'login': login, 'key': key}, f)

        top = Toplevel(self.parent)
        top.title("Success!")
        top.geometry('230x50')
        msg = 'The software has been activated! Enjoy!'
        msg = Message(top, text=msg, aspect=500)
        msg.grid()

        self.__init__(self.parent)

    def deploy_activation_widgets(self, frame):
        self.license = StringVar()
        license_key_label = Label(self.frame, text='Enter the license key:')
        license_key_label.grid(row=0, column=0, pady=5, sticky=W)
        self.license_key_entry = Entry(frame)
        self.license_key_entry.grid(row=0, column=1, pady=5, padx=5, sticky=W)
        check_license_bttn = Button(self.frame, text='Check license',
                                    command=lambda: self.check_license(frame),
                                    relief=GROOVE)
        check_license_bttn.grid(sticky=W, padx=20, pady=5)
        frame.grid(row=0, column=0)

    def check_rucaptcha_key(self):
        if not self.rucaptcha_api_key.get():
            raise RuCaptchaError('Rucaptcha API key is not specified')

        resp = requests.post('http://rucaptcha.com/res.php',
                             data={'key': self.rucaptcha_api_key.get().strip(),
                                   'action': 'getbalance'})
        logger.info(resp.text)
        if 'ERROR_ZERO_BALANCE' in resp.text:
            raise RuCaptchaError('')
        elif 'ERROR_WRONG_USER_KEY' in resp.text or 'ERROR_KEY_DOES_NOT_EXIST' in resp.text:
            raise RuCaptchaError('API key is wrong')

    @staticmethod
    def get_node():
        mac = uuid.getnode()
        if (mac >> 40) % 2:
            raise OSError('Не удается авторизовать устройство. Обратитесь в тех.поддержку.')
        return hex(mac)

    def start_process(self):
        if len(threading.enumerate()) == 1:
            t = threading.Thread(target=self.run_process)
            t.daemon = True
            t.start()

    def accounts_open(self):
        dir = (os.path.dirname(self.accounts_path)
               if self.accounts_path is not None else '.')
        accounts_path = askopenfilename(
                    title='login:pass accounts data',
                    initialdir=dir,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)

        self.accounts_path = self.load_file(accounts_path, self.old_accounts, r"[\d\w]+:.+\n?$")

    def old_account_generator(self):
        start = 0
        end = span = self.accounts_per_number.get()
        while start < len(self.old_accounts):
            yield self.old_accounts[start:end]
            start, end = end, end + span

    def email_boxes_open(self):
        dir_ = (os.path.dirname(self.email_boxes_path)
                if self.email_boxes_path is not None else '.')
        email_boxes_path = askopenfilename(
                    title='Email addresses',
                    initialdir=dir_,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)

        self.email_boxes_path = self.load_file(email_boxes_path, self.email_boxes_data, r"[\d\w]+@[\d\w]+\.\w+:.+\n?$")

    def manifest_open(self):
        dir_ = (os.path.dirname(self.manifest_path)
                if self.manifest_path is not None else '.')
        manifest_path = askopenfilename(
                    title='SDA manifest',
                    initialdir=dir_,
                    filetypes=[('manifest', '*.json')],
                    defaultextension='.json', parent=self.parent)
        if manifest_path:
            return self.load_manifest(manifest_path)

    def load_manifest(self, manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                self.manifest_data = json.load(f)
            self.manifest_path = manifest_path
        except (EnvironmentError, TypeError):
            return

        self.status_bar.set("File loaded: %s" % os.path.basename(manifest_path))

    def proxy_open(self):
        dir_ = (os.path.dirname(self.proxy_path)
                if self.proxy_path is not None else '.')
        proxy_path = askopenfilename(
            title='Proxy',
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=self.parent)

        self.proxy_path = self.load_file(proxy_path, self.proxy_data,
                                         "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}:\d{1,5}\n?$")

    def load_file(self, path, data, regexr):
        if not path:
            return ''
        try:
            with open(path, 'r') as f:
                for row, item in enumerate(f.readlines()):
                    if not re.match(regexr, item):
                        self.add_log("Unacceptable value: {0} in row {1}".format(item.strip(), row))
                        continue
                    data.append(item.strip())
        except (EnvironmentError, TypeError):
            return ''

        if data:
            self.status_bar.set("File loaded: %s" % os.path.basename(path))
            return path

    def app_quit(self, *ignore):
        with open('database/userdata.txt', 'w') as f:
            json.dump(self.userdata, f)

        self.parent.destroy()


class RegistrationThread(threading.Thread):

    counter = 0
    lock = threading.Lock()
    email_lock = threading.Lock()

    def __init__(self, window, amount, result=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.window = window
        self.amount = amount
        self.result = result
        self.error = None

    def run(self):
        while RegistrationThread.counter < self.amount:
            with RegistrationThread.lock:
                RegistrationThread.counter += 1
            try:
                self.registrate_account()
            except Exception as err:
                self.error = (err.__class__.__name__, err)
                logger.critical(traceback.format_exc())
                return

    def registrate_account(self):
        login, passwd, email = steamreg.create_account_web(self.window.rucaptcha_api_key.get().strip(),
                                                           thread_lock=RegistrationThread.email_lock)
        logger.info('Account: %s:%s', login, passwd)
        self.window.add_log('Account created: %s %s' % (login, passwd))

        with RegistrationThread.lock:
            if not self.window.mobile_bind.get():
                self.save_unattached_account(login, passwd)
        steam_client = SteamClient()
        while True:
            try:
                with RegistrationThread.lock:
                    time.sleep(3)
                    steam_client.login(login, passwd)
                break
            except AttributeError as err:
                logger.error(err)
                time.sleep(3)

        steamreg.activate_account(steam_client)
        steamreg.remove_intentory_privacy(steam_client)
        if self.result is not None:
            self.result.append((login, passwd, email))

    def save_unattached_account(self, login, passwd):
        with open('accounts.txt', 'a+') as f:
            f.write('%s:%s\n' % (login, passwd))


class Binder:

    def __init__(self, window, sms_service):
        self.window = window
        self.sms_service = sms_service
        self.error = None

    def bind_accounts(self, accounts_package):
        tzid, number, is_repeated = self.get_new_number()
        self.window.status_bar.set('Setting up Mobile Guard...')
        for account_data in accounts_package:
            login, passwd = account_data[:2]
            try:
                email = account_data[2]
            except IndexError:
                email = ""
            logger.info('Account: %s:%s', login, passwd)
            insert_log = self.log_wrapper(login)
            insert_log('Phone number: ' + number)
            insert_log('Signing in...')
            try:
                steam_client = steamreg.mobile_login(login, passwd)
            except SteamAuthError as err:
                insert_log(err)
                continue

            if steamreg.is_phone_attached(steam_client):
                insert_log('Mobile guard has already been set up')
                continue

            try:
                sms_code, mobguard_data, number, tzid = self.add_authenticator(insert_log, steam_client,
                                                                               number, tzid, is_repeated)
            except SteamAuthError:
                error = 'Can"t set up mobile guard: ' + login
                logger.error(error)
                insert_log(error)
                continue
            is_repeated = True
            insert_log('Making a request to set up mobile guard...')
            steamreg.finalize_authenticator_request(steam_client, mobguard_data, sms_code)
            mobguard_data['account_password'] = passwd
            offer_link = steamreg.fetch_tradeoffer_link(steam_client)
            self.save_attached_account(mobguard_data, login, passwd, number, offer_link, email)
            if not self.window.autoreg.get():
                steamreg.activate_account(steam_client)
                steamreg.remove_intentory_privacy(steam_client)
            insert_log('Mobile guard has been set up successfully')

        self.sms_service.set_operation_ok(tzid)

    def add_authenticator(self, insert_log, steam_client, number, tzid, is_repeated):
        while True:
            insert_log('Making a request to add the phone number...')
            response = steamreg.addphone_request(steam_client, number)
            if not response['success']:
                if "we couldn't send an SMS to your phone" in response.get('error_text', ''):
                    insert_log('Steam replied that it failed to add the phone number ')
                    insert_log('Changing number...')
                    tzid, number, is_repeated = self.get_new_number(tzid)
                    insert_log('Новый номер: ' + number)
                    time.sleep(5)
                    continue
                raise SteamAuthError('Steam addphone request failed: %s' % number)

            insert_log('Waiting for sms code...')
            try:
                sms_code = self.sms_service.get_sms_code(tzid, is_repeated)
                if not is_repeated:
                    is_repeated = True
                if not sms_code:
                    insert_log('Can"t receive the SMS. Trying again...')
                    continue
            except OnlineSimError:
                insert_log('The time of phone number rental has expired: ' + number)
                insert_log('Changing phone number...')
                tzid, number, is_repeated = self.get_new_number(tzid)
                insert_log('New phone number: ' + number)
                continue

            mobguard_data = steamreg.add_authenticator_request(steam_client)
            response = steamreg.checksms_request(steam_client, sms_code)
            if 'The SMS code is incorrect' in response.get('error_text', ''):
                insert_log('Invalid sms code %s. Trying again...' % sms_code)
                continue
            return sms_code, mobguard_data, number, tzid

    def get_new_number(self, tzid=0):
        if tzid:
            self.sms_service.set_operation_ok(tzid)
            self.sms_service.used_codes.clear()
        is_repeated = False
        tzid = self.sms_service.request_new_number(country=self.window.country_code.get())
        number = self.sms_service.get_number(tzid)
        return tzid, number, is_repeated

    def save_attached_account(self, mobguard_data, login, passwd, number, offer_link, email):
        if self.window.autoreg.get():
            accounts_dir = 'new_accounts'
            if self.window.fold_accounts.get():
                accounts_dir = os.path.join(accounts_dir, login)
                os.makedirs(accounts_dir)
        else:
            accounts_dir = 'loaded_accounts'

        steamid = mobguard_data['Session']['SteamID']
        txt_path = os.path.join(accounts_dir, login + '.txt')
        mafile_path = os.path.join(accounts_dir, login + '.maFile')
        binding_date = datetime.date.today()
        revocation_code = mobguard_data['revocation_code']
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('{login}:{passwd}\nMobile Guard set up date: {binding_date}\nPhone number: {number}\n'
                    'SteamID: {steamid}\nEmail: {email}\nRCODE: {revocation_code}\nTrade offer link: {offer_link}'.format(**locals()))

        with open('accounts_guard.txt', 'a+') as f:
            f.write('%s:%s\n' % (login, passwd))

        if self.window.import_mafile.get():
            sda_path = os.path.join(os.path.dirname(self.window.manifest_path), login + '.maFile')
            data = {
                "encryption_iv": None,
                "encryption_salt": None,
                "filename": login + '.maFile',
                "steamid": int(steamid)
            }
            self.window.manifest_data["entries"].append(data)
            with open(self.window.manifest_path, 'w') as f1, open(sda_path, 'w') as f2:
                json.dump(self.window.manifest_data, f1)
                json.dump(mobguard_data, f2, separators=(',', ':'))

        with open(mafile_path, 'w') as f:
            json.dump(mobguard_data, f, separators=(',', ':'))

    def log_wrapper(self, login):
        def insert_log(text):
            self.window.add_log('%s (%s)' % (text, login))
        return insert_log


root = Tk()
window = MainWindow(root)
root.iconbitmap('database/app.ico')
root.title('Steam Auto Authenticator v0.8')
root.protocol("WM_DELETE_WINDOW", window.app_quit)
root.mainloop()
