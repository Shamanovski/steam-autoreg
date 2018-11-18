import sys
import uuid
import shelve

app = sys.argv[1]
if app not in ("farmtools", "autoreg"):
    raise Exception("Wrong app")
try:
    key = sys.argv[2]
except IndexError:
    key = None

files = {"farmtools": "farmtools_keys.txt", "autoreg": "keys.txt"}
dbs = {"farmtools": "farmtools_db", "autoreg": "clients"}

if key:
    command = sys.argv[3]
    if command == "delete":
        with shelve.open('database/' + dbs[app]) as db:
            del db[key]
else:
    with open('database/' + files[app], 'a+') as f:
        id_ = str(uuid.uuid4())
        f.write(id_ + '\n')

    print(id_)