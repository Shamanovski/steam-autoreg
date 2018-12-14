from tkinter import *
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showwarning, askyesno, showinfo
import datetime
import os
import traceback
import threading
import asyncio
from collections import namedtuple
from queue import Queue, Empty
from proxybroker import Broker
import pyqiwi

from sms_services import *
from steamreg import *
from enums import *


logger = logging.getLogger('__main__')

for dir_name in ('new_accounts', 'loaded_accounts'):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

if not os.path.exists('database/userdata.txt'):
    with open('database/userdata.txt', 'w') as f:
        f.write('{}')

if not os.path.exists("database/imap-hosts.json"):
    with open("database/imap-hosts.json", "w") as f:
        f.write("{}")

with open("database/interface_states.json", "r") as f:
    STATES = json.load(f)

loop = asyncio.get_event_loop()
Account = namedtuple("Account", ['login', 'password', 'email', 'email_password'])


class MainWindow:

    def __init__(self, parent):
        self.parent = parent
        self.frame = Frame(self.parent)
        self.is_running = False
        self.software_product_key = StringVar()
        self.registration_quota = IntVar()
        self.binding_quota = IntVar()
        with open('database/userdata.txt', 'r') as f:
            self.userdata = json.load(f)

        success = self.authorize_user()
        if not success:
            self.deploy_activation_widgets()

        self.queue = asyncio.Queue(loop=loop)
        self.accounts = Queue()
        self.reg_proxies = Queue()
        self.bind_proxies = Queue()

        self.number_countries = {}

        self.start_time = time.time()

        self.proxy_broker = None

        self.manifest_path = ''
        self.accounts_path = ''
        self.email_boxes_path = ''
        self.proxy_path = ''
        self.proxy_urls_path = ''
        self.real_names_path = ''
        self.countries_path = ''
        self.avatars_path = ''
        self.statuses_path = ''

        self.real_names = []
        self.countries = []
        self.avatars = []
        self.statuses = []
        self.proxy_data = []
        self.proxy_urls = []
        self.privacy_settings = {}
        self.email_boxes_data = []
        self.old_accounts = []
        self.imap_hosts = {}
        self.manifest_data = None

        self.autoreg = IntVar()
        self.import_mafile = IntVar()
        self.mobile_bind = IntVar()
        self.fold_accounts = IntVar()
        self.use_mail_repeatedly = IntVar()
        self.add_money_to_account = IntVar()
        self.generate_emails = IntVar()
        self.remove_emails_from_file = IntVar()
        self.activate_profile = IntVar()
        self.selection_type = IntVar()
        self.selection_type.set(int(SelectionType.RANDOM))
        self.sms_service_type = IntVar()
        self.sms_service_type.set(int(SmsService.OnlineSim))
        self.captcha_service_type = IntVar()
        self.captcha_service_type.set(int(CaptchaService.RuCaptcha))

        self.activation_code = StringVar()
        self.onlinesim_api_key = StringVar()
        self.captcha_api_key = StringVar()
        self.qiwi_api_key = StringVar()
        self.free_games = StringVar()
        self.paid_games = StringVar()
        self.new_accounts_amount = IntVar()
        self.accounts_per_number = IntVar()
        self.amount_of_binders = IntVar()
        self.amount_of_binders.set(1)
        self.private_email_boxes = IntVar()
        self.accounts_per_proxy = IntVar()
        self.accounts_per_proxy.set(100)
        self.status_bar = StringVar()
        self.country_code = StringVar()
        self.country_code.set('Россия')
        self.proxy_type = IntVar()
        self.dont_use_local_ip = IntVar()
        self.pass_login_captcha = IntVar()
        self.money_to_add = IntVar()
        self.captcha_host = StringVar()
        self.onlinesim_host = StringVar()
        self.imap_host = StringVar()
        self.email_domains = StringVar()

        self.accounts_registrated_stat = StringVar()
        self.accounts_registrated_stat.set("Accounts registrated:")
        self.accounts_binded_stat = StringVar()
        self.accounts_binded_stat.set("Accounts binded:")
        self.captcha_balance_stat = StringVar()
        self.captcha_balance_stat.set("Captcha service balance:")
        self.captchas_resolved_stat = StringVar()
        self.captchas_resolved_stat.set("Captchas resolved successfully")
        self.captchas_failed_stat = StringVar()
        self.captchas_failed_stat.set("Captchas resolved unsuccessfully:")
        self.captchas_expenses_stat = StringVar()
        self.captchas_expenses_stat.set("Expenses on captchas:")
        self.numbers_used_stat = StringVar()
        self.numbers_used_stat.set("Numbers used:")
        self.onlinesim_balance_stat = StringVar()
        self.onlinesim_balance_stat.set("SIM service balance:")
        self.numbers_failed_stat = StringVar()
        self.numbers_failed_stat.set("Invalid numbers:")
        self.numbers_expenses_stat = StringVar()
        self.numbers_expenses_stat.set("Expenses on SIM numbers:")
        self.accounts_unregistrated_stat = StringVar()
        self.accounts_unregistrated_stat.set("Accounts for registration left:")
        self.accounts_unbinded_stat = StringVar()
        self.accounts_unbinded_stat.set("Accounts for binding left:")
        self.proxies_loaded_stat = StringVar()
        self.proxies_loaded_stat.set("Proxies in queue:")
        self.proxies_limited_stat = StringVar()
        self.proxies_limited_stat.set("Proxies limited on Steamm:")
        self.proxies_bad_stat = StringVar()
        self.proxies_bad_stat.set("Invalid Proxies:")
        self.time_stat = StringVar()
        self.time_stat.set("Time left: 0")

        self.login_template = StringVar()
        self.nickname_template = StringVar()
        self.passwd_template = StringVar()

        self.menubar = Menu(parent)
        parent['menu'] = self.menubar

        self.product_key_label = Label(self.frame, text="Product key:")

        self.product_key_entry = Entry(self.frame, width=37, textvariable=self.software_product_key, state="readonly")

        self.accounts_per_number_label = Label(self.frame, text='Amount of accounts per number:')
        self.accounts_per_number_entry = Entry(self.frame, textvariable=self.accounts_per_number,
                                               width=2, disabledforeground='#808080')

        self.onlinesim_settings_bttn = Button(self.frame, text='Set up SIM service',
                                              command=self.deploy_onlinenum_window, bg='#CEC8C8', relief=GROOVE)

        self.new_accounts_amount_label = Label(self.frame, text='Amount of accounts for registration:')
        self.new_accounts_amount_entry = Entry(self.frame, textvariable=self.new_accounts_amount, width=4, disabledforeground='#808080')
        self.captcha_api_key_label = Label(self.frame, text='Captcha api key:')
        self.captcha_api_key_entry = Entry(self.frame, textvariable=self.captcha_api_key, disabledforeground='#808080')

        self.captcha_settings_bttn = Button(self.frame, text='Set up captcha service',
                                            command=self.deploy_captcha_window, bg='#CEC8C8', relief=GROOVE)

        tools_frame = Frame(self.parent)
        self.tools_label = Label(tools_frame, text='Tools:')
        self.options_label = Label(tools_frame, text='Options:')
        self.autoreg_checkbutton = Checkbutton(tools_frame, text='Create new accounts',
                                               variable=self.autoreg, command=self.set_states,
                                               disabledforeground='#808080')
        self.use_mail_repeatedly_checkbutton = Checkbutton(tools_frame, text='Use emails repeatedly',
                                                           variable=self.use_mail_repeatedly, command=self.set_states,
                                                           disabledforeground='#808080')
        self.add_money_to_account_checkbutton = Checkbutton(tools_frame, text='Deposit money on accounts',
                                                            variable=self.add_money_to_account)

        self.mafile_checkbutton = Checkbutton(tools_frame, text='Import maFile into SDA',
                                              variable=self.import_mafile, command=self.set_states,
                                              disabledforeground='#808080')
        self.mobile_bind_checkbutton = Checkbutton(tools_frame, text='Set up mobile guard',
                                                   variable=self.mobile_bind, command=self.set_states,
                                                   disabledforeground='#808080')
        self.fold_accounts_checkbutton = Checkbutton(tools_frame, text='Stock items at folders',
                                                     variable=self.fold_accounts, disabledforeground='#808080')
        self.amount_of_binders_label = Label(tools_frame, text='Number of threads for binding:')
        self.amount_of_binders_field = Entry(tools_frame, textvariable=self.amount_of_binders,
                                             disabledforeground='#808080', width=2)

        self.start_button = Button(tools_frame, text='Start', command=self.start_process,
                                   bg='#CEC8C8', relief=GROOVE, width=50)
        tools_frame.grid(row=1, column=0, pady=5)

        log_frame = Frame(self.parent)
        self.log_label = Label(log_frame, text='Logs:')
        self.scrollbar = Scrollbar(log_frame, orient=VERTICAL)
        self.scrollbar_x = Scrollbar(log_frame, orient=HORIZONTAL)
        self.log_box = Listbox(log_frame, yscrollcommand=self.scrollbar.set, xscrollcommand=self.scrollbar_x.set)
        self.log_box.bind('<Enter>', self.freeze_log)
        self.log_box.bind('<Leave>', self.unfreeze_log)
        self.log_frozen = False
        self.scrollbar["command"] = self.log_box.yview
        self.scrollbar.bind('<Enter>', self.freeze_log)
        self.scrollbar.bind('<Leave>', self.unfreeze_log)

        self.scrollbar_x["command"] = self.log_box.xview
        self.scrollbar_x.bind('<Enter>', self.freeze_log)
        self.scrollbar_x.bind('<Leave>', self.unfreeze_log)

        self.frame.grid(row=0, column=0, sticky=W)
        log_frame.columnconfigure(0, weight=999)
        log_frame.columnconfigure(1, weight=1)
        log_frame.grid(row=2, column=0, sticky=NSEW)

        self.status_bar_label = Label(log_frame, anchor=W, text='Ready...', textvariable=self.status_bar)
        self.caption_label = Label(log_frame, text='by Shamanovsky')

        if self.userdata:
            self.set_attributes()
        self.load_files()
        self.set_countries()

        self.pack_widgets()

    def set_states(self):
        for checkbutton_name, configs in sorted(STATES.items(), key=lambda item: item[1]["priority"]):
            try:
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
            except AttributeError:
                continue

    @staticmethod
    def adjust_state(flag, state):
        reversed_states = {NORMAL: DISABLED, DISABLED: NORMAL}
        if not flag:
            state = reversed_states[state]
        return state

    def set_attributes(self):
        for attr_name, value in self.userdata.items():
            try:
                attribute = self.__getattribute__(attr_name)
            except AttributeError:
                continue
            try:
                attribute.set(value)
            except AttributeError:
                self.__setattr__(attr_name, value)

    def load_files(self):
        self.load_manifest(self.manifest_path)
        self.load_file(self.email_boxes_path, self.email_boxes_data)
        self.load_file(self.accounts_path, self.old_accounts)
        self.load_file(self.proxy_path, self.proxy_data)
        self.load_file(self.proxy_urls_path, self.proxy_urls)
        self.load_file(self.avatars_path, self.avatars)
        self.load_file(self.statuses_path, self.statuses)
        self.load_file(self.countries_path, self.countries)
        self.load_file(self.real_names_path, self.real_names)

    def pack_widgets(self):
        self.load_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Load...", menu=self.load_menu)
        self.load_menu.add_command(label="Own accounts", command=self.accounts_open)
        self.load_menu.add_command(label="Own emails", command=self.email_boxes_open)
        self.load_menu.add_command(label="Own proxy list", command=self.proxy_open)
        self.load_menu.add_command(label="SDA Manifest", command=self.manifest_open)

        self.menubar.add_cascade(label="Set up proxy", command=self.deploy_proxy_widget)
        self.menubar.add_cascade(label="Show statistics", command=self.deploy_stats_window)
        self.menubar.add_cascade(label="Set up template", command=self.deploy_template_window)
        self.menubar.add_cascade(label="Extra", command=self.deploy_additional_settings_window)
        self.menubar.add_cascade(label="Activate code", command=self.deploy_code_activation_window)

        self.product_key_label.grid(row=4, column=0, padx=5, pady=5, sticky=W)
        self.product_key_entry.grid(row=5, padx=5, column=0, pady=5, sticky=W)

        self.onlinesim_settings_bttn.grid(row=0, column=0, padx=3, pady=5, sticky=W)

        self.captcha_settings_bttn.grid(row=1, column=0, padx=3, pady=5, sticky=W)

        self.new_accounts_amount_label.grid(row=2, column=0, pady=5, sticky=W)
        self.new_accounts_amount_entry.grid(row=2, column=1, pady=5, padx=5, sticky=W)

        self.accounts_per_number_label.grid(row=3, column=0, pady=5, sticky=W)
        self.accounts_per_number_entry.grid(row=3, column=1, pady=5, padx=5, sticky=W)

        self.tools_label.grid(row=0, column=0, pady=3, sticky=W)
        self.autoreg_checkbutton.grid(row=1, column=0, sticky=W)
        self.mobile_bind_checkbutton.grid(row=1, column=1, pady=1, sticky=W)
        self.options_label.grid(row=2, column=0, pady=3, sticky=W)

        self.use_mail_repeatedly_checkbutton.grid(row=3, column=0, pady=1, sticky=W)
        self.mafile_checkbutton.grid(row=3, column=1, pady=1, sticky=W)
        self.fold_accounts_checkbutton.grid(row=4, column=1, pady=1, sticky=W)
        self.add_money_to_account_checkbutton.grid(row=4, column=0, pady=1, sticky=W)
        self.amount_of_binders_label.grid(row=5, column=0, pady=1, sticky=W)
        self.amount_of_binders_field.grid(row=5, column=1, columnspan=2, pady=1, sticky=W)

        self.start_button.grid(row=6, pady=10, columnspan=2)
        self.log_label.grid(row=0, column=0, pady=5, sticky=W)
        self.log_box.grid(row=1, column=0, sticky=NSEW)
        self.scrollbar.grid(row=1, column=1, sticky=NS)
        self.scrollbar_x.grid(row=2, column=0, sticky=EW)
        self.status_bar_label.grid(row=3, column=0, columnspan=2, sticky=W, pady=5)
        self.caption_label.grid(row=3, column=0, sticky=E)
        self.set_states()

    def deploy_stats_window(self):
        top = Toplevel(master=self.frame)
        top.title("Statistics")
        top.iconbitmap('database/stats.ico')

        Label(top, text="Quota").grid(row=0, padx=5, column=0, pady=5, sticky=W)

        Label(top, text="Registration:").grid(row=1, padx=5, column=0, pady=5, sticky=W)

        Label(top, textvariable=self.registration_quota).grid(row=1, padx=5, column=0, pady=5)

        Label(top, text="Binding:").grid(row=1, padx=5, column=1, pady=5, sticky=W)
        Label(top, textvariable=self.binding_quota).grid(row=1, padx=5, column=1, pady=5)

        lbl14 = Label(top, text="Accounts")
        lbl14.grid(row=3, column=0, padx=5, pady=5, sticky=W)

        lbl = Label(top, textvariable=self.accounts_registrated_stat)
        lbl.grid(row=4, column=0, padx=5, pady=5, sticky=W)

        lbl2 = Label(top, textvariable=self.accounts_binded_stat)
        lbl2.grid(row=4, column=1, padx=5, pady=5, sticky=W)

        lbl3 = Label(top, textvariable=self.accounts_unregistrated_stat)
        lbl3.grid(row=5, column=0, padx=5, pady=10, sticky=W)

        lbl4 = Label(top, textvariable=self.accounts_unbinded_stat)
        lbl4.grid(row=5, column=1, padx=5, pady=10, sticky=W)

        lbl13 = Label(top, text="Captchas")
        lbl13.grid(row=6, column=0, padx=5, pady=5, sticky=W)

        lbl16 = Label(top, textvariable=self.captcha_balance_stat)
        lbl16.grid(row=7, column=0, padx=5, pady=5, sticky=W)

        lbl5 = Label(top, textvariable=self.captchas_resolved_stat)
        lbl5.grid(row=7, column=1, padx=5, pady=5, sticky=W)

        lbl6 = Label(top, textvariable=self.captchas_failed_stat)
        lbl6.grid(row=8, column=0, padx=5, pady=5, sticky=W)

        lbl7 = Label(top, textvariable=self.captchas_expenses_stat)
        lbl7.grid(row=8, column=1, padx=5, pady=10, sticky=W)

        lbl15 = Label(top, text="Numbers")
        lbl15.grid(row=9, column=0, padx=5, pady=5, sticky=W)

        Label(top, textvariable=self.onlinesim_balance_stat).grid(row=10, column=0, padx=5, pady=5, sticky=W)

        lbl8 = Label(top, textvariable=self.numbers_expenses_stat)
        lbl8.grid(row=10, column=1, padx=5, pady=5, sticky=W)

        lbl8 = Label(top, textvariable=self.numbers_used_stat)
        lbl8.grid(row=11, column=0, padx=5, pady=5, sticky=W)

        lbl8 = Label(top, textvariable=self.numbers_failed_stat)
        lbl8.grid(row=11, column=1, padx=5, pady=10, sticky=W)

        lbl16 = Label(top, text="Proxy")
        lbl16.grid(row=12, column=0, padx=5, pady=5, sticky=W)

        lbl9 = Label(top, textvariable=self.proxies_loaded_stat)
        lbl9.grid(row=15, column=0, padx=5, pady=5, sticky=W)

        lbl10 = Label(top, textvariable=self.proxies_limited_stat)
        lbl10.grid(row=15, column=1, padx=5, pady=5, sticky=W)

        lbl11 = Label(top, textvariable=self.proxies_bad_stat)
        lbl11.grid(row=16, column=1, padx=5, pady=10, sticky=W)

        lbl12 = Label(top, textvariable=self.time_stat)
        lbl12.grid(row=17, column=0, padx=5, pady=15, sticky=W)

    def deploy_code_activation_window(self):
        def activate_code():
            resp = requests.get("https://shamanovski.pythonanywhere.com/validatecode", params={
                "key": self.software_product_key.get(), "uniquecode": code.get()
            }).json()
            message = resp["message"]
            success = resp["success"]
            if success:
                quota = resp["quota"]
                amount = resp["amount"] * 10
                if quota == "registration_quota":
                    self.registration_quota.set(self.registration_quota.get() + amount)
                elif quota == "binding_quota":
                    self.binding_quota.set(self.binding_quota.get() + amount)

            showwarning("Code activation", message)
            top.destroy()

        top = Toplevel(master=self.frame)
        top.title("Code activation")
        code = StringVar()
        Label(top, text="Code:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=code, width=30) \
            .grid(row=0, column=1, padx=5, pady=5, sticky=W)

        Button(top, command=activate_code, text="Confirm").grid(column=0, columnspan=2, row=1, padx=5, pady=5)

    def deploy_additional_settings_window(self):
        def add_imap_host():
            if not self.imap_host.get() or not self.email_domains.get():
                showinfo("Message", "Specify IMAP server and email domains related to it", parent=top)
                return
            self.imap_hosts[self.imap_host.get()] = self.email_domains.get().split(",")
            showinfo("Message", "IMAP server and email domains related to it has been added", parent=top)

        def list_imap_hosts(top):
            top = Toplevel(master=top)
            top.title("IMAP servers")
            row = 0
            for imap_server, email_domains in self.imap_hosts.items():
                Label(top, text="%s: %s" % (imap_server, ", ".join(email_domains)))\
                    .grid(column=0, row=row, pady=5)
                row += 1

        top = Toplevel(master=self.frame)
        top.iconbitmap('database/plus-blue.ico')
        top.title("Additional features")
        Label(top, text="Add games (comma seprated list of appids):").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.free_games, width=30) \
            .grid(row=0, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Deposit money on accounts").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Label(top, text="QIWI Api Key:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.qiwi_api_key, width=30) \
            .grid(row=3, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Amount of money (in rubles):").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.money_to_add, width=5) \
            .grid(row=4, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Emails").grid(row=5, column=0, padx=5, pady=5, sticky=W)
        Checkbutton(top, text="Generate emails", variable=self.generate_emails) \
            .grid(row=6, column=0, padx=5, pady=5, sticky=W)
        Checkbutton(top, text="Delete used emails from text file", variable=self.remove_emails_from_file) \
            .grid(row=7, column=0, padx=5, pady=5, sticky=W)

        Label(top, text="IMAP сервер:").grid(column=0, row=8, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.imap_host, width=30) \
            .grid(row=8, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Domains (with a comma without spaces)").grid(column=0, row=9, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.email_domains, width=30) \
            .grid(row=9, column=1, padx=5, pady=5, sticky=W)

        Button(top, text="Add", command=add_imap_host) \
            .grid(row=10, column=0, padx=5, pady=5, sticky=W)

        Label(top, text="Product key").grid(row=4, column=0, padx=5, pady=5, sticky=W)
        Button(top, text="Enter product key", command=self.deploy_activation_widgets)\
            .grid(column=0, row=5, padx=5, pady=5, sticky=W)

        Button(top, command=top.destroy, text="Confirm").grid(column=0, columnspan=2, row=6, padx=5, pady=5)
        Label(top, text="Notes").grid(row=15, column=0, padx=5, pady=5, sticky=W)
        Label(top, text="game subid can be found on steamdb.info (for example https://steamdb.info/app/730/subs/)"
                        "\nor in the source code of the page of the game on the steam store"
                        "\n\nGenerate emails means that you use one loaded email where\n"
                        "all mails from generated emails are redirected to",
              justify=LEFT).grid(column=0, columnspan=2, row=16, padx=5, sticky=W)

        Button(top, command=top.destroy, text="Подтвердить").grid(column=0, columnspan=2, row=17, padx=5, pady=5)

    def deploy_template_window(self):
        top = Toplevel(master=self.frame)
        top.title("Templates")
        Label(top, text="Login template:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.login_template, width=20)\
            .grid(row=0, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Password template:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.passwd_template, width=20)\
            .grid(row=1, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Profile nickname template:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        Entry(top, textvariable=self.nickname_template, width=20)\
            .grid(row=2, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Type of selection from lists:").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        rbttn = Radiobutton(top, text="Random", variable=self.selection_type, value=int(SelectionType.RANDOM))
        rbttn.grid(column=0, row=4, padx=5, pady=5, sticky=W)
        rbttn2 = Radiobutton(top, text="Sequential", variable=self.selection_type, value=int(SelectionType.CONSISTENT))
        rbttn2.grid(column=1, row=4, padx=5, pady=5, sticky=W)
        Label(top, text="If you want your nicknames to be generated randomly, leave it empty.\n"
                        "If you want your nickname to be the same as login write {login}", justify=LEFT)\
            .grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=W)

        Label(top, text="List elements selection type:").grid(row=4, column=0, padx=5, pady=5, sticky=W)
        rbttn = Radiobutton(top, text="Random", variable=self.selection_type, value=int(SelectionType.RANDOM))
        rbttn.grid(column=0, row=5, padx=5, pady=5, sticky=W)
        rbttn2 = Radiobutton(top, text="Consistent", variable=self.selection_type, value=int(SelectionType.CONSISTENT))
        rbttn2.grid(column=1, row=5, padx=5, pady=5, sticky=W)

        Label(top, text="Real names:").grid(row=5, column=0, padx=5, pady=5, sticky=W)
        Button(top, text="Load", relief=GROOVE, command=lambda: self.file_open(top, "real_names_path", "Real names", self.real_names, r".+\n"))\
            .grid(row=5, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Countries:").grid(row=6, column=0, padx=5, pady=5, sticky=W)
        Button(top, text="Load", relief=GROOVE, command=lambda: self.file_open(top, "countries_path", "Countries", self.countries, r"\w\w\n"))\
            .grid(row=6, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Avatars:").grid(row=7, column=0, padx=5, pady=5, sticky=W)
        Button(top, text="Load", relief=GROOVE, command=lambda: self.file_open(top, "avatars_path", "Avatars", self.avatars, r"https?://.+\n"))\
            .grid(row=7, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Statuses:").grid(row=8, column=0, padx=5, pady=5, sticky=W)
        Button(top, text="Load", relief=GROOVE, command=lambda: self.file_open(top, "statuses_path", "Statuses", self.statuses, r".+\n"))\
            .grid(row=8, column=1, padx=5, pady=5, sticky=W)

        Label(top, text="Example of login template(password or nickname):\nmy{num}login or qwerty{num},\n"
                        "where the num is automatically converted into the index number by software\n\n"
                        "Countries are specified in ISO 3166-1 Alpha 2 format (for example: RU, US)\n\n"
                        "Avatars: URL links to images")\
            .grid(row=9, columnspan=2, padx=5, pady=5, sticky=W)

        Button(top, command=top.destroy, text="Confirm").grid(column=0, columnspan=2, row=10, padx=5, pady=5)

    def add_log(self, message):
        self.log_box.insert(END, message)
        if not self.log_frozen:
            self.log_box.yview(END)

    def freeze_log(self, *ignore):
        self.log_frozen = True

    def unfreeze_log(self, *ignore):
        self.log_frozen = False

    def run_process(self):
        self.save_input()
        new_accounts_amount = self.new_accounts_amount.get()
        onlinesim_api_key = self.onlinesim_api_key.get()
        sim_host = self.onlinesim_host.get()
        reg_threads = []
        bind_threads = []
        if self.mobile_bind.get():
            if self.sms_service_type.get() == SmsService.OnlineSim:
                sms_service = OnlineSimApi(onlinesim_api_key, sim_host)
            elif self.sms_service_type.get() == SmsService.SmsActivate:
                sms_service = SmsActivateApi(onlinesim_api_key, sim_host)
            quota_queue = Queue()
            for _ in range(self.binding_quota.get()):
                quota_queue.put(False)
            quota_queue.put(True)
            for _ in range(self.amount_of_binders.get()):
                t = Binder(self, sms_service, self.accounts_per_number.get(), quota_queue)
                t.start()
                bind_threads.append(t)
        if self.autoreg.get():
            reg_threads = self.init_threads(new_accounts_amount)
            Binder.total_amount = self.new_accounts_amount.get()
        else:
            self.put_from_text_file()
            Binder.total_amount = len(self.old_accounts)

        for thread in reg_threads:
            thread.join()
        RegistrationThread.is_alive = False

        for thread in bind_threads:
            thread.join()

        self.is_running = False
        self.status_bar.set('Ready...')

    def check_input(self):
        if not self.manifest_path and self.import_mafile.get():
            showwarning("Error", "The path to the SDA manifest is not specified",
                        parent=self.parent)
            return False

        if not self.proxy_path and self.proxy_type.get() == Proxy.File:
            showwarning("Error", "The path to proxies list file is not specified",
                        parent=self.parent)
            return False

        if not self.proxy_urls_path and self.proxy_type.get() == Proxy.Url:
            showwarning("Error", "The path to proxies links list file is not specified",
                        parent=self.parent)
            return False

        if self.autoreg.get():
            if self.registration_quota.get() == 0:
                showwarning("Error", "Insufficient quota for registration. "
                                      "Pay for quota to start registrating")
                return False
            try:
                self.check_templates()
            except ValueError as err:
                showwarning("Error in template", err, parent=self.parent)

            if not self.captcha_api_key.get():
                showwarning("Error", 'Captcha service api key is not specified')
                return False
            try:
                self.check_captcha_key()
            except Exception as err:
                showwarning("Error Captcha", err, parent=self.parent)
                return False
            try:
                if self.new_accounts_amount.get() <= 0:
                    raise ValueError
            except (TclError, ValueError):
                showwarning("Error", "The amount of accounts for registration is not specified",
                            parent=self.parent)
                return False

            if not self.email_boxes_data:
                showwarning("Error", "Emails are not loaded")
                return False

            if self.paid_games.get():
                is_agree = askyesno("Games purchasing", "Are you sure you want to buy games on accounts?",
                                    icon='warning')
                if not is_agree:
                    return False

            if self.add_money_to_account.get():
                if not self.money_to_add.get():
                    showwarning("Error", "Amount of money for depositing is not specified")
                    return False

                if not self.qiwi_api_key.get():
                    showwarning("Error", "QIWI API key is not specified")
                    return False

                is_agree = askyesno("Money depositing", "Are you sure you want deposit money on accounts?",
                                    icon='warning')
                if not is_agree:
                    return False

        if self.mobile_bind.get():
            if self.binding_quota.get() == 0:
                showwarning("Error", "Insufficient quota for binding. Pay for quota to start binding")
                return False
            try:
                if not 0 < self.accounts_per_number.get() <= 30:
                    raise ValueError
            except (TclError, ValueError):
                showwarning("Error", "Specify amount of accounts per phone number less than 30 and more than 0",
                            parent=self.parent)
                return False

            try:
                if not 0 < self.amount_of_binders.get() <= 10:
                    raise ValueError
            except (TclError, ValueError):
                showwarning("Error", "Specify the correct number of threads less than 11",
                            parent=self.parent)
                return False

            onlinesim_api_key = self.onlinesim_api_key.get()
            if not onlinesim_api_key:
                showwarning("Error", "SIM service api key is not specified", parent=self.parent)
                return False

            if not self.accounts_path and not self.autoreg.get():
                showwarning("Error", "Path to accounts credentials is not specified "
                                      "If you don't own existing accounts, check 'Registrate new accounts'",
                            parent=self.parent)
                return False

        return True

    def save_input(self):
        exceptions = ('status_bar', 'license', 'stat', 'quota')
        for field, value in self.__dict__.items():
            if list(filter(lambda exception: exception in field, exceptions)) or "status" in field:
                continue
            if issubclass(value.__class__, Variable) or 'path' in field or 'imap_hosts' in field:
                try:
                    value = value.get()
                except (AttributeError, TypeError):
                    pass
                self.userdata[field] = value

    def init_threads(self, threads_amount=20):
        RegistrationThread.left = self.new_accounts_amount.get()
        threads = []
        quota_queue = Queue()
        for _ in range(self.registration_quota.get()):
            quota_queue.put(False)
        quota_queue.put(True)
        if threads_amount > 20:
            threads_amount = 20
        for _ in range(threads_amount):
            t = RegistrationThread(self, quota_queue)
            t.start()
            threads.append(t)
        return threads

    def authorize_user(self):
        if os.path.exists('database/key.txt'):
            with open('database/key.txt', 'r') as f:
                user_data = json.load(f)
            url = 'https://shamanovski.pythonanywhere.com/'
            data = {
                'key': user_data['key']
            }
            resp = requests.post(url, data=data, timeout=10, attempts=3).json()
            self.registration_quota.set(resp["data"]["registration_quota"])
            self.binding_quota.set(resp["data"]["binding_quota"])
        else:
            return False

        return resp['success_x001']

    def generate_key(self):
        login = self.login_entry.get()
        if not login:
            showwarning("Error", "Specify login")
            return
        resp = requests.get("https://shamanovski.pythonanywhere.com/generate-product-key", params={"login": login})
        if resp.status_code == 406:
            showwarning("Error", "Login is already in use.")
            return
        self.software_product_key.set(resp.text)

    def check_key(self, top):
        key = self.software_product_key.get()
        if not key:
            showwarning('Error', 'Specify product key', parent=self.parent)
            return
        url = 'https://shamanovski.pythonanywhere.com/'
        data = {
            'key': key
        }
        resp = requests.post(url, data=data, timeout=10, attempts=3).json()

        if not resp['success_x001']:
            showwarning('Error', "ey was not found. Specify the key correctly or generate a new one",
                        parent=self.parent)
            return

        with open('database/key.txt', 'w') as f:
            json.dump({'key': key}, f)
        data = resp["data"]
        self.registration_quota.set(data["registration_quota"])
        self.binding_quota.set(data["binding_quota"])
        top.destroy()

    def deploy_activation_widgets(self):
        top = Toplevel(master=self.frame)
        top.title("Product key")
        self.license = StringVar()
        license_key_label = Label(top, text='Enter product key')
        license_key_label.grid(row=0, column=0, pady=5, sticky=W)
        self.license_key_entry = Entry(top, width=37, textvariable=self.software_product_key)
        self.license_key_entry.grid(row=0, column=1, pady=5, padx=5, sticky=W)
        login_label = Label(top, text='Your login (any):')
        login_label.grid(row=1, column=0, pady=5, sticky=W)
        self.login_entry = Entry(top)
        self.login_entry.grid(row=1, column=1, pady=5, padx=5, sticky=W)
        check_license_bttn = Button(top, text='Generate a product key',
                                    command=self.generate_key,
                                    relief=GROOVE)
        check_license_bttn.grid(sticky=W, padx=5, pady=5)

        check_license_bttn = Button(top, text='Confirm',
                                    command=lambda: self.check_key(top),
                                    relief=GROOVE)
        check_license_bttn.grid(column=0, columnspan=2, padx=5, pady=5)

    async def produce_proxies(self):
        if not self.proxy_type.get():
            return
        pass_login_captcha = self.pass_login_captcha.get()
        ctr = 0
        while True:
            proxy = await self.queue.get()
            if proxy is None:
                return
            try:
                ban = steamreg.check_proxy_ban(proxy)
            except (ProxyError, ConnectionError, Timeout):
                self.add_log("Unstable connection %s" % (proxy if proxy else "local ip"))
                continue
            if ban and pass_login_captcha:
                self.add_log("%s: need to resolve captchas to autorize"
                                    % (str(proxy).strip("<>") if proxy else "local ip"))
                continue

            self.reg_proxies.put(proxy)
            self.bind_proxies.put(proxy)
            ctr += 1
            self.proxies_loaded_stat.set("Proxies in queue: %d" % ctr)

    def deploy_proxy_widget(self):
        def set_state():
            type = self.proxy_type.get()
            for widget in (load_proxy_list_bttn, load_proxy_bttn):
                state = NORMAL if widget.value == type else DISABLED
                widget.configure(state=state)

        top = Toplevel(master=self.frame)
        top.title("Proxy set up")
        top.iconbitmap('database/proxy.ico')
        checkbttn = Checkbutton(top, text="Don't use local IP if proxy is used", variable=self.dont_use_local_ip)
        checkbttn.grid(column=0, row=0, pady=5, sticky=W)

        checkbttn2 = Checkbutton(top, text="\nMiss proxy where \ncaptchas resolving is needed to authorize",
                                 variable=self.pass_login_captcha)
        checkbttn2.grid(column=1, row=0, pady=5, sticky=W)

        lbl = Label(top, text="Proxy type:")
        lbl.grid(column=0, row=1, padx=5, pady=10, sticky=W)
        Label(top, text='Количество аккаунтов на 1 прокси:').grid(row=1, column=0, pady=5, sticky=W)
        Entry(top, width=3, textvariable=self.accounts_per_proxy).grid(row=1, column=1, pady=5, padx=5, sticky=W)

        lbl = Label(top, text="Тип проксирования:")
        lbl.grid(column=0, row=2, padx=5, pady=10, sticky=W)

        rbttn1 = Radiobutton(top, command=set_state, text="Search for public proxies", variable=self.proxy_type,
                             value=int(Proxy.Public))
        rbttn1.grid(column=0, row=3, padx=5, pady=5, sticky=W)

        rbttn2 = Radiobutton(top, command=set_state, text="Load links to proxy lists:",
                             variable=self.proxy_type, value=int(Proxy.Url))
        rbttn2.grid(column=0, row=4, padx=5, pady=5, sticky=W)

        load_proxy_list_bttn = Button(top, state=DISABLED, text="Load", command=lambda: self.proxy_list_open(top),
                                      relief=GROOVE)
        load_proxy_list_bttn.grid(column=0, row=5, padx=10, pady=5, sticky=W)
        load_proxy_list_bttn.value = int(Proxy.Url)

        rbttn3 = Radiobutton(top, command=set_state, text="Load own proxies:", variable=self.proxy_type,
                             value=int(Proxy.File))
        rbttn3.grid(column=0, row=6, padx=5, pady=5, sticky=W)

        load_proxy_bttn = Button(top, state=DISABLED, text="Load", command=lambda: self.proxy_open(top),
                                 relief=GROOVE)
        load_proxy_bttn.grid(column=0, row=7, padx=10, pady=5, sticky=W)
        load_proxy_bttn.value = int(Proxy.File)

        rbttn4 = Radiobutton(top, command=set_state, text="Don't use proxy", variable=self.proxy_type, value=0)
        rbttn4.grid(column=0, row=7, padx=5, pady=5, sticky=W)

        confirm_bttn = Button(top, command=top.destroy, text="Confirm")
        confirm_bttn.grid(column=0, columnspan=2, row=8, padx=5, pady=5)

        for rbttn in (rbttn1, rbttn2, rbttn3, rbttn4):
            if self.proxy_type.get() == rbttn.config("value"):
                rbttn.select()
                break

        set_state()
        top.focus_set()

    def deploy_onlinenum_window(self):
        def deploy_countries_list(event=True):
            self.number_countries.clear()
            self.set_countries()
            if event:
                self.country_code.set("Russia")

                if self.sms_service_type.get() == SmsService.OnlineSim:
                    self.onlinesim_host.set("onlinesim.ru")
                elif self.sms_service_type.get() == SmsService.SmsActivate:
                    self.onlinesim_host.set("sms-activate.ru")

            OptionMenu(top, self.country_code, *sorted(self.number_countries.keys())) \
                .grid(row=5, padx=5, pady=5, sticky=W)

        top = Toplevel(master=self.frame)
        top.title("SIM service configuration")
        top.iconbitmap('database/sim.ico')

        Label(top, text='Service:').grid(row=0, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='OnlineSim', variable=self.sms_service_type, value=int(SmsService.OnlineSim),
                    command=deploy_countries_list).grid(row=1, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='SMS Activate', variable=self.sms_service_type, value=int(SmsService.SmsActivate),
                    command=deploy_countries_list).grid(row=1, column=1, pady=5, padx=5, sticky=W)

        Label(top, text='api key:').grid(row=2, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_api_key, width=33)\
            .grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Host:').grid(row=3, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.onlinesim_host, width=33, )\
            .grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Country:').grid(row=4, column=0, pady=3, sticky=W)
        deploy_countries_list(event=False)

        Button(top, command=top.destroy, text="Confirm").grid(column=0, columnspan=3, row=6, padx=5, pady=5)

    def set_countries(self):
        if self.sms_service_type.get() == SmsService.SmsActivate:
            countries_string = "0 - Russia, 1 - Ukraine, 2 - Kazakhstan, 3 - China, 4 - Philippines 5 - Myanmar, " \
                               "6 - Indonesia, 7 - Malaysia, 8 - Kenya, 9 - Tanzania, 10 - Vietnam, 11 - Kyrgyzstan," \
                               " 12 - USA, 13 - Israel, 14 - HonkKong, 15 - Poland, 16 - UK, " \
                               "17 - Madagascar, 18 - Kongo, 19 - Nigeria, 20 - Macao, 21 - Egypt, 23 - Ireland, " \
                               "24 - Cambodia"
            for item in countries_string.split(", "):
                value, delimiter, country = item.partition(" - ")
                self.number_countries[country] = value

        elif self.sms_service_type.get() == SmsService.OnlineSim:
            self.number_countries = {
                "Russia": "7",
                "China": "86",
                "Nigeria": "234",
                "Kot'd'ivuar": "225",
                "Ukraine": "380",
                "Kazakhstan": "77",
                "Egypt": "20"
            }

    def deploy_captcha_window(self):
        top = Toplevel(master=self.frame)
        top.title("Captcha service set up")
        top.iconbitmap('database/captcha.ico')

        Label(top, text='Service:').grid(row=0, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='RuCaptcha', variable=self.captcha_service_type, value=int(CaptchaService.RuCaptcha))\
            .grid(row=1, column=0, pady=5, padx=5, sticky=W)
        Radiobutton(top, text='AntiCaptcha', variable=self.captcha_service_type, value=int(CaptchaService.AntiCaptcha))\
            .grid(row=1, column=1, pady=5, padx=5, sticky=W)

        Label(top, text='api key:').grid(row=2, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.captcha_api_key, width=33) \
            .grid(row=2, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Label(top, text='Host:').grid(row=3, column=0, pady=5, padx=5, sticky=W)
        Entry(top, textvariable=self.captcha_host, width=33) \
            .grid(row=3, column=1, columnspan=2, pady=5, padx=5, sticky=W)

        Button(top, command=top.destroy, text="Confirm").grid(column=0, columnspan=3, row=4, padx=5, pady=5)

    def check_captcha_key(self):
        balance = steamreg.captcha_service.get_balance()
        self.captcha_balance_stat.set("Captcha service balance: %s" % balance)

    def start_process(self):
        if self.is_running:
            return
        steamreg.set_captcha_service()
        if not self.check_input():
            return
        if self.generate_emails.get():
            self.use_mail_repeatedly.set(1)
        self.update_clock()
        self.is_running = True
        t = threading.Thread(target=self.init_proxy_producing)
        t.daemon = True
        t.start()

        t = threading.Thread(target=self.run_process)
        t.daemon = True
        t.start()

    def init_proxy_producing(self):
        proxy_type = self.proxy_type.get()
        if not self.dont_use_local_ip.get() or proxy_type == Proxy.Local:
            self.reg_proxies.put(None)
            self.bind_proxies.put(None)
        if proxy_type == Proxy.Local:
            return
        providers = None
        if proxy_type == Proxy.Url:
            providers = self.proxy_urls
        self.proxy_broker = Broker(queue=self.queue, loop=loop, providers=providers)

        types = [('HTTP', ('Anonymous', 'High')), 'HTTPS', 'SOCKS4', 'SOCKS5']
        data = None
        if proxy_type == Proxy.File:
            with open(self.proxy_path) as f:
                data = f.read()
        asyncio.ensure_future(self.proxy_broker.find(
            data=data, types=types), loop=loop)
        self.status_bar.set("Checking proxies...")
        loop.run_until_complete(self.produce_proxies())
        loop.close()
        self.status_bar.set("")
        self.add_log("Finished proxies checking")

    def accounts_open(self):
        dir = (os.path.dirname(self.accounts_path)
               if self.accounts_path is not None else '.')
        accounts_path = askopenfilename(
                    title='login:pass accounts data',
                    initialdir=dir,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)

        self.accounts_path = self.load_file(accounts_path, self.old_accounts, r"[\d\w]+:.+\n")

    def put_from_text_file(self):
        for item in self.old_accounts:
            email, email_password = None, None
            try:
                login, password, email, email_password = item.split(':')[:4]
            except ValueError:
                login, password = item.split(':')[:2]
            account = Account(login, password, email, email_password)
            self.accounts.put(account)
        RegistrationThread.is_alive = False

    def email_boxes_open(self):
        dir_ = (os.path.dirname(self.email_boxes_path)
                if self.email_boxes_path is not None else '.')
        email_boxes_path = askopenfilename(
                    title='Email addresses',
                    initialdir=dir_,
                    filetypes=[('Text file', '*.txt')],
                    defaultextension='.txt', parent=self.parent)

        self.email_boxes_path = self.load_file(email_boxes_path, self.email_boxes_data, r"[\d\w\-\.]+@[\d\w]+\.\w+:.+\n")

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
        except (EnvironmentError, TypeError, json.JSONDecodeError):
            return

        self.status_bar.set("File loaded: %s" % os.path.basename(manifest_path))

    def proxy_open(self, window):
        dir_ = (os.path.dirname(self.proxy_path)
                if self.proxy_path is not None else '.')
        proxy_path = askopenfilename(
            title='Proxy',
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=window)

        self.proxy_path = self.load_file(proxy_path, self.proxy_data)
        window.destroy()

    def proxy_list_open(self, window):
        dir_ = (os.path.dirname(self.proxy_path)
                if self.proxy_path is not None else '.')
        proxy_urls_path = askopenfilename(
            title='Proxy URLS',
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=window)

        self.proxy_urls_path = self.load_file(proxy_urls_path, self.proxy_urls)

    def file_open(self, window, path, title, collection, regexr=None):
        path_attr = getattr(self, path)
        dir_ = (os.path.dirname(path_attr)
                if path is not None else '.')
        input_path = askopenfilename(
            title=title,
            initialdir=dir_,
            filetypes=[('Text file (.txt)', '*.txt')],
            defaultextension='.txt', parent=window)

        path_string = self.load_file(input_path, collection, regexr)
        setattr(self, path, path_string)

    def load_file(self, path, data, regexr=None):
        if not path:
            return ''
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for row, item in enumerate(f.readlines()):
                    if regexr and not re.match(regexr, item):
                        self.add_log("Unacceptable value: {0} in row {1}".format(item.strip(), row))
                        if not item.endswith("\n"):
                            self.add_log("New line is absent (type Enter at the end of the row)")
                        continue
                    data.append(item.strip())
        except (EnvironmentError, TypeError):
            # showwarning("Ошибка", "Не удается открыть указанный файл", parent=self.parent)
            return ''

        if data:
            self.add_log("File loaded: %s" % os.path.basename(path))
            return path

    def update_clock(self):
        now = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
        self.time_stat.set("Time left: %s" % now)
        self.parent.after(1000, self.update_clock)

    def app_quit(self, *ignore):
        self.save_input()
        with open('database/userdata.txt', 'w') as f:
            json.dump(self.userdata, f)

        steamreg.counters_db.sync()
        steamreg.counters_db.close()

        if self.remove_emails_from_file.get():
            with open(self.email_boxes_path, "w") as f:
                for email in self.email_boxes_data:
                    f.write(email + "\n")

        # with open("accounts.txt", "w") as f:
        #     while not self.accounts.empty():
        #         f.write(self.accounts.get() + "\n")

        requests.post("https://shamanovski.pythonanywhere.com/updatequota", data={
            "registration_quota": self.registration_quota.get(),
            "binding_quota": self.binding_quota.get(),
            "key": self.software_product_key.get()
        })

        self.parent.destroy()

    def check_templates(self):
        for template in (self.login_template, self.passwd_template, self.nickname_template):
            value = template.get()
            if value and "{num}" not in value:
                raise ValueError("Template is incorrect: " + value)


class RegistrationThread(threading.Thread):

    left = 0
    counter = 0
    proxy_limited = 0
    proxy_invalid = 0

    error = False

    lock = threading.Lock()

    is_alive = True

    def __init__(self, window, quota_queue):
        super().__init__()
        self.daemon = True

        self.client = window
        self.quota_queue = quota_queue
        self.proxy = None

    def run(self):
        self.set_proxy()
        while self.left > 0:
            quota_expired = self.quota_queue.get()
            if quota_expired:
                return
            with self.lock:
                self.left -= 1
            if self.counter > 0 and self.counter % self.client.accounts_per_proxy.get() == 0:
                self.set_proxy()
            try:
                self.registrate_account()
            except (ProxyError, ConnectionError, Timeout):
                self.client.add_log("Unstable connection: %s" % (self.proxy if self.proxy else "local ip"))
                self.set_proxy()
                with self.lock:
                    self.left += 1
                self.proxy_invalid += 1
                self.client.proxies_bad_stat.set("Invalid proxies: %d" % self.proxy_limited)
            except Exception as err:
                with self.lock:
                    if not self.error:
                        showwarning("Error %s" % err.__class__.__name__, err)
                        logger.critical(traceback.format_exc())
                        self.error = True
                return
            if self.counter % 50 == 0:
                self.client.check_captcha_key()
            self.client.check_captcha_key()

    def registrate_account(self):
        self.client.status_bar.set('Creating accounts, resolving captchas...')
        try:
            login, passwd, email, email_password = steamreg.create_account_web(self.proxy)
        except LimitReached as err:
            logging.error(err)
            if self.proxy:
                self.client.add_log("Registration limit has been reached: %s. Changing proxy..." % self.proxy)
            else:
                self.client.add_log("Registration limit has been reached for local ip.")
            self.proxy_limited += 1
            self.client.proxies_limited_stat.set("Proxies limited on Steam: %d" % self.proxy_limited)
            self.set_proxy()
            return

        logger.info('Account: %s:%s', login, passwd)
        self.client.add_log('Account has been registered (%s, %s, %s)' % (self.proxy, login, passwd))

        with self.lock:
            self.save_unattached_account(login, passwd, email, email_password)
            self.client.registration_quota.set(self.client.registration_quota.get() - 1)
        try:
            steam_client = steamreg.login(login, passwd, self.proxy, self.client,
                                          pass_login_captcha=self.client.pass_login_captcha.get())
        except AuthException as err:
            logger.error(err)
            self.client.add_log("%s: can't authorize from this IP"
                                % (str(self.proxy).strip("<>") if self.proxy else "local ip"))
            self.set_proxy()
            return
        except SteamAuthError as err:
            logger.error(err)
            self.client.add_log(err)
            return
        except CaptchaRequired as err:
            logger.error(err)
            self.client.add_log("%s: captcha resolving is needed to authorize"
                                % (str(self.proxy).strip("<>") if self.proxy else "local ip"))
            self.set_proxy()
            return

        if self.client.activate_profile.get():
            selection_type = self.client.selection_type.get()
            summary = self.select_profile_data(self.client.statuses, selection_type)
            real_name = self.select_profile_data(self.client.real_names, selection_type)
            country = self.select_profile_data(self.client.countries, selection_type)
            steamreg.activate_account(steam_client, summary, real_name, country)
            steamreg.edit_profile(steam_client)
            self.client.add_log("Profile has been activated: %s:%s" % (login, passwd))

        if self.client.avatars:
            if self.client.selection_type.get() == SelectionType.RANDOM:
                avatar = random.choice(self.client.avatars)
            elif self.client.selection_type.get() == SelectionType.CONSISTENT:
                avatar = self.client.avatars.pop(0)

            match = re.match(r"https?://.+", str(avatar))
            if match is not None:  # str(avatar) if avatar is a link
                avatar_link = match.group()
                avatar = requests.get(avatar_link).content
                try:
                    self.client.avatars.remove(avatar_link)
                except ValueError:
                    pass
                self.client.avatars.append(avatar)

            steamreg.upload_avatar(steam_client, avatar)

        if self.client.add_money_to_account.get():
            self.add_money(login)

        if self.client.free_games.get() or self.client.paid_games.get():
            steam_client.session.get("http://store.steampowered.com")
        if self.client.free_games.get():
            self.add_free_games(steam_client)
        if self.client.paid_games.get():
            self.purchase_games(steam_client)

        account = Account(login, passwd, email, email_password)
        self.client.accounts.put(account)
        self.counter += 1
        self.client.accounts_registrated_stat.set("Accounts registered: %d" % self.counter)
        self.client.accounts_registrated_stat.set("Accounts for registration left : %d" %
                                                  (self.client.new_accounts_amount.get() - self.counter))

    def set_proxy(self):
        if self.proxy is not None:
            self.proxy.close()

        proxy = None
        try:
            proxy = self.client.reg_proxies.get(timeout=60)
        except Empty:
            quit()

        if proxy:
            self.client.add_log("Regger: " + str(proxy).strip("<>"))
        else:
            self.client.add_log("Regger: Using the local ip")
        self.proxy = proxy

    def add_free_games(self, steam_client):
        appids = self.client.free_games.get().replace(" ", "").split(",")
        data = {
            'action': 'add_to_cart',
            'sessionid': steam_client.session.cookies.get('sessionid', domain='store.steampowered.com')
        }
        for subid in appids:
            data['subid'] = int(subid)
            resp = steam_client.session.post('https://store.steampowered.com/checkout/addfreelicense', data=data)

    def purchase_games(self, steam_client):
        appids = self.client.paid_games.get().replace(" ", "").split(",")
        sessionid = steam_client.session.cookies.get('sessionid', domain='store.steampowered.com')
        data = {"action": "add_to_cart", "sessionid": sessionid, "snr": "1_5_9__403"}
        for appid in appids:
            data["subid"] = int(appid)
            resp = steam_client.session.post("https://store.steampowered.com/cart/", data=data)
        resp = steam_client.session.get("https://store.steampowered.com/checkout/?purchasetype=self",
                                        params={"purchasetype": "self"})
        cart_id = re.search(r"id=\"shopping_cart_gid\" value=\"(\d+)\">", resp.text).group(1)
        data = {
            "gidShoppingCart": cart_id,
            "gidReplayOfTransID": -1,
            "PaymentMethod": "steamaccount",
            "abortPendingTransactions": 0,
            "bHasCardInfo": 0,
            "Country": "RU",
            "bIsGift": 0,
            "GifteeAccountID": 0,
            "ScheduledSendOnDate": 0,
            "bSaveBillingAddress": 1,
            "bUseRemainingSteamAccount": 1,
            "bPreAuthOnly": 0,
            "sessionid": sessionid
        }
        resp = steam_client.session.post("https://store.steampowered.com/checkout/inittransaction/", data=data).json()
        trans_id = resp["transid"]
        resp = steam_client.session.post("https://store.steampowered.com/checkout/finalizetransaction/",
                                         data={"transid": trans_id})

    def add_money(self, login):
        wallet = pyqiwi.Wallet(token=self.client.qiwi_api_key.get())
        payment = wallet.send(pid="25549", recipient=login, amount=int(self.client.money_to_add.get()))

    @staticmethod
    def select_profile_data(data, type):
        result = ""
        if data:
            if type == SelectionType.RANDOM:
                result = random.choice(data)
            elif type == SelectionType.CONSISTENT:
                result = data.pop(0)
                data.append(result)

        return result

    @staticmethod
    def save_unattached_account(login, passwd, email, email_password):
        with open('accounts.txt', 'a+') as f:
            f.write('%s:%s:%s:%s\n' % (login, passwd, email, email_password))

        with open(r'new_accounts/%s.txt' % login, 'w') as f:
            f.write('%s:%s\nEmail: %s:%s' % (login, passwd, email, email_password))


class Binder(threading.Thread):

    lock = threading.Lock()

    binded_counter = 0
    binding_total = 0
    numbers_ordered_counter = 0
    numbers_failed_counter = 0

    error = False

    def __init__(self, window, sms_service, amount, quota_queue):
        super().__init__()
        self.client = window
        self.quota_queue = quota_queue
        self.amount = amount
        self.sms_service = sms_service
        self.number = None
        self.proxy = None
        self.used_codes = []

    def run(self):
        self.set_proxy()
        while True:
            quota_expired = self.quota_queue.get()
            if quota_expired:
                return
            if self.binded_counter > 0 and self.binded_counter % self.client.accounts_per_proxy.get() == 0:
                self.set_proxy()
            pack = []
            with self.lock:
                self.fill_pack(pack)
            if not pack:
                return

            try:
                with self.lock:
                    self.get_new_number()

                for account in pack:
                    while True:
                        try:
                            self.bind_account(account)
                            break
                        except (ProxyError, ConnectionError, Timeout):
                            self.client.add_log("Unstable connection: %s"
                                                % (self.proxy if self.proxy else "local ip"))
                            self.set_proxy()
                self.client.onlinesim_balance_stat.set("SIM service balance: %s" % self.sms_service.get_balance())
            except Exception as err:
                with self.lock:
                    if not self.error:
                        showwarning("Error %s" % err.__class__.__name__, err)
                        logger.critical(traceback.format_exc())
                        self.error = True
                return

            self.sms_service.set_operation_ok(self.number['tzid'])

    def fill_pack(self, pack):
        for _ in range(self.amount):
            while True:
                try:
                    account = self.client.accounts.get(timeout=30)
                    pack.append(account)
                    break
                except Empty:
                    if not RegistrationThread.is_alive:
                        return

    def bind_account(self, account):
        self.client.status_bar.set('Setting up Mobile Guard...')
        login, passwd, email, email_password = account.login, account.password, account.email, account.email_password
        logger.info('Account: %s:%s', login, passwd)
        insert_log = self.log_wrapper(login)
        insert_log('Phone number: ' + self.number['number'])
        insert_log('Signing in...')
        try:
            steam_client = steamreg.mobile_login(login, passwd, self.proxy, email, email_password,
                                                 pass_login_captcha=self.client.pass_login_captcha.get())
        except AuthException as err:
            logger.error(err)
            self.client.add_log("%s: can't authorize from this ip"
                                % (str(self.proxy).strip("<>") if self.proxy else "local ip"))
            self.set_proxy()
            return
        except SteamAuthError as err:
            insert_log(err)
            return
        except CaptchaRequired as err:
            logger.error(err)
            insert_log("%s: captchas resolving is needed to authorize"
                       % (str(self.proxy).strip("<>") if self.proxy else "local ip"))
            self.set_proxy()
            return

        if steamreg.is_phone_attached(steam_client):
            insert_log('Mobile guard has already been set up')
            return

        try:
            sms_code, mobguard_data = self.add_authenticator(insert_log, steam_client)
        except SteamAuthError as err:
            error = "Can't bind number to the account: %s. Error: %s" % (login, err)
            logger.error(error)
            insert_log(error)
            self.numbers_failed_counter += 1
            self.client.numbers_failed_stat.set("Invalid numbers: %s" % self.numbers_failed_counter)
            self.get_new_number(self.number['tzid'])
            return
        steamreg.finalize_authenticator_request(steam_client, mobguard_data, sms_code)
        mobguard_data['account_password'] = passwd
        offer_link = steamreg.fetch_tradeoffer_link(steam_client)
        self.save_attached_account(mobguard_data, account, self.number['number'], offer_link)
        self.client.binding_quota.set(self.client.binding_quota.get() - 1)
        if not self.client.autoreg.get() and self.client.activate_profile.get():
            steamreg.activate_account(steam_client, "", "", "")
            steamreg.edit_profile(steam_client)
            self.client.add_log("Profile activated: %s:%s" % (login, passwd))
        insert_log('Guard has been activated successfully')
        self.binded_counter += 1
        self.client.accounts_binded_stat.set("Accounts binding: %d" % self.binded_counter)
        self.client.accounts_binded_stat.set("Accounts for binding left: %d" % (self.binding_total - self.binded_counter))

    def add_authenticator(self, insert_log, steam_client):
        while True:
            insert_log('Making a request to add the phone number...')
            response = steamreg.addphone_request(steam_client, self.number['number'])
            if not response['success']:
                if "we couldn't send an SMS to your phone" in response.get('error_text', ''):
                    insert_log('Steam responded that it could not deliver the SMS')
                    insert_log('Changing the number...')
                    self.get_new_number(self.number['tzid'])
                    insert_log('New number: ' + self.number['number'])
                    time.sleep(5)
                    continue
                raise SteamAuthError(response.get('error_text', None))

            insert_log('Waiting for sms code...')
            attempts = 0
            success = False
            try:
                while attempts < 15:
                    if self.number['is_repeated']:
                        self.sms_service.request_repeated_number_usage(self.number['tzid'])
                    attempts += 1
                    sms_code = self.sms_service.get_sms_code(self.number['tzid'])
                    if sms_code and sms_code not in self.used_codes:
                        self.used_codes.append(sms_code)
                        success = True
                        break
                    time.sleep(4)
            except (OnlineSimError, SmsActivateError) as err:
                insert_log("Error onlinesim: %s" % err)
                self.get_new_number(self.number['tzid'])
                insert_log('New number: ' + self.number['number'])
                continue

            if not success:
                insert_log('The sms is unreachable. Trying again...')
                self.get_new_number(self.number['tzid'])
                continue

            self.number['is_repeated'] = True

            insert_log('Making an attempt to activate Guard...')
            mobguard_data = steamreg.add_authenticator_request(steam_client)
            response = steamreg.checksms_request(steam_client, sms_code)
            if 'The SMS code is incorrect' in response.get('error_text', ''):
                insert_log('Invalid sms code %s. Trying again...' % sms_code)
                continue
            return sms_code, mobguard_data

    def get_new_number(self, tzid=0):
        if tzid:
            self.sms_service.set_operation_ok(tzid)
            self.used_codes.clear()
        is_repeated = False
        self.numbers_ordered_counter += 1
        self.client.numbers_used_stat.set("Numbers used: %s" % self.numbers_ordered_counter)
        tzid, number = self.sms_service.get_number(country=self.client.number_countries[self.client.country_code.get()])
        self.number = {'tzid': tzid, 'number': number, 'is_repeated': is_repeated}

    def save_attached_account(self, mobguard_data, account, number, offer_link):
        if self.client.autoreg.get():
            accounts_dir = 'new_accounts'
        else:
            accounts_dir = 'loaded_accounts'

        if self.client.fold_accounts.get():
            accounts_dir = os.path.join(accounts_dir, account.login)
            os.makedirs(accounts_dir)

        steamid = mobguard_data['Session']['SteamID']
        txt_path = os.path.join(accounts_dir, account.login + '.txt')
        mafile_path = os.path.join(accounts_dir, account.login + '.maFile')
        binding_date = datetime.date.today()
        revocation_code = mobguard_data['revocation_code']
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('{account.login}:{account.password}\nMobile Guard set up date: {binding_date}\nPhone number: {number}\n'
                    'SteamID: {steamid}\nRCODE: {revocation_code}\nTrade offer link: {offer_link}\n'
                    'Email: {account.email}\nEmail password: {account.email_password}'.format(**locals()))

        with open('accounts_guard.txt', 'a+') as f:
            f.write('%s:%s\n' % (account.login, account.password))

        if self.client.import_mafile.get():
            sda_path = os.path.join(os.path.dirname(self.client.manifest_path), account.login + '.maFile')
            data = {
                "encryption_iv": None,
                "encryption_salt": None,
                "filename": account.login + '.maFile',
                "steamid": int(steamid)
            }
            self.client.manifest_data["entries"].append(data)
            with open(self.client.manifest_path, 'w') as f1, open(sda_path, 'w') as f2:
                json.dump(self.client.manifest_data, f1)
                json.dump(mobguard_data, f2, separators=(',', ':'))

        with open(mafile_path, 'w') as f:
            json.dump(mobguard_data, f, separators=(',', ':'))

    def set_proxy(self):
        if self.proxy is not None:
            self.proxy.close()

        proxy = self.client.bind_proxies.get()

        if proxy:
            self.client.add_log("Binder: " + str(proxy).strip("<>"))
        else:
            self.client.add_log("Binder: Using the local ip")
        self.proxy = proxy

    def log_wrapper(self, login):
        def insert_log(text):
            self.client.add_log('%s (%s)' % (text, login))
        return insert_log


def launch():
    root = Tk()
    window = MainWindow(root)
    global steamreg
    steamreg = SteamRegger(window)
    root.iconbitmap('database/app.ico')
    root.title('Steam Auto Authenticator v1.2.0')
    root.protocol("WM_DELETE_WINDOW", window.app_quit)
    root.mainloop()


if __name__ == '__main__':
    logging.getLogger("requests").setLevel(logging.ERROR)
    logger = logging.getLogger(__name__)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler = logging.FileHandler('database/logs.txt', 'w', encoding='utf-8')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

launch()
