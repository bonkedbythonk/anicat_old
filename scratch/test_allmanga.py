import requests
import re

url = "https://allmanga.to/bangumi/ReooPAxPMsHM4KPMY"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
nuxt_data = re.search(r'window\.__NUXT__=(.*?);</script>', resp.text)
if nuxt_data:
    print(nuxt_data.group(1)[:1000])
else:
    print("No NUXT data found")
