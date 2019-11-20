import requests
import sys

feature, key, quota_amount = sys.argv[1:]

data = {"key": key, "binding_quota": 0}
if feature == "binding":
    data["binding_quota"] = quota_amount
else:
    raise ValueError("Задана несуществующая функция")


resp = requests.post("http://shamanovski.pythonanywhere.com/updatequota", data=data)
print(resp.text)
