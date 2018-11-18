import requests
import sys

feature, key, quota_amount = sys.argv[1:]

data = {"key": key, "registration_quota": 0, "binding_quota": 0}
if feature == "registration":
    data["registration_quota"] = quota_amount
elif feature == "binding":
    data["binding_quota"] = quota_amount
else:
    raise ValueError("Задана несуществующая функция")


resp = requests.post("http://shamanovski.pythonanywhere.com/addquota", data=data)
print(resp.text)
