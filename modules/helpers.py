adminIds = [
    368894926,
    500610349,
    164527323,
    50967453,
    173414196,
    77080264
]


def isAdmin(chatId: int=-1):
    if chatId > 0:
        return chatId in adminIds
    else:
        return adminIds


def getLink(msg):
    if "entities" in msg:
        links = [x for x in msg["entities"] if x["type"] == "url"]
        if links:
            link = links[0]
            return msg["text"][link["offset"]:(link["offset"]+link["length"])].strip()
    return None


def short(url):
    from requests import utils, post

    escaped = url
    if "https://" not in url and "http://" not in url:
        escaped = "http://" + url

    headers = {
        "Authorization": "Bearer e8de1a5482420f3dbd0790fdffa93ba6e415d7f9",
        "Content-Type": "application/json"
    }
    params = {
        "long_url": utils.requote_uri(escaped)
    }

    try:
        response = post("https://api-ssl.bitly.com/v4/shorten", json=params, headers=headers)
        data = response.json()
        linkId = data["id"].replace("amzn.to/", "").replace("bit.ly/", "")
        return linkId
    except Exception:
        if url.startswith("http://bit.ly/") or url.startswith("https://bit.ly/") or url.startswith("bit.ly/") \
            or url.startswith("http://amzn.to/") or url.startswith("https://amzn.to/") or url.startswith("amzn.to/"):
            return url.split("/")[-1]
        return None
