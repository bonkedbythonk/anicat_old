import requests
from bs4 import BeautifulSoup

url = "https://allmanga.to/bangumi/ReooPAxPMsHM4KPMY"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')
# Find elements that might contain the data
print("Title:", soup.title.text if soup.title else None)
for div in soup.find_all('div', limit=20):
    text = div.text.strip()
    if text:
        print("Div:", text[:50].replace('\n', ' '))
