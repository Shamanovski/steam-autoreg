import requests
import sys
import pprint

method, value = sys.argv[1], sys.argv[2]

resp = requests.get("http://shamanovski.pythonanywhere.com/searchdb", params={"method": method, "value": value})
resp = resp.json()
pprint.pprint(resp)
