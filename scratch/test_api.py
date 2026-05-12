import requests
import json

headers = {"Referer": "https://allmanga.to/", "User-Agent": "Mozilla/5.0"}
url = "https://api.allanime.day/api"
q = 'query($search: SearchInput, $limit: Int, $page: Int, $translationType: VaildTranslationTypeEnumType, $countryOrigin: VaildCountryOriginEnumType) { shows(search: $search, limit: $limit, page: $page, translationType: $translationType, countryOrigin: $countryOrigin) { pageInfo { total } edges { _id name availableEpisodes englishName type } } }'
payload = {
    "query": q,
    "variables": {
        "search": {"query": "one piece", "allowAdult": False, "allowUnknown": False},
        "limit": 40,
        "page": 1,
        "translationType": "sub",
        "countryOrigin": "ALL"
    }
}
resp = requests.get(url, params={"variables": json.dumps(payload["variables"]), "query": q}, headers=headers)
print(resp.status_code)
print(resp.text[:500])
