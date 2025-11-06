from flask import Flask, render_template
import json
app = Flask(__name__)

@app.route('/')
def root():
    retrieveData()
    return render_template('index.html', title=retrieveData())

import requests
import sys

def retrieveData():
    url = "https://comicvine.gamespot.com/api/"
    req = "https://comicvine.gamespot.com/api/search/?api_key=2b739459da8dc4ec62f68656b642554dea026eca&format=json&resources=character&query=Superman"

    headers = {
        'Host': 'comicvine.gamespot.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Cookie': 'device_view=full; xcab=3-0; patcv=UGhvZW5peFxVc2VyQnVuZGxlXEVudGl0eVxVc2VyOllXeGpiM0pmY0dsdVpYTT06MjA3NjMxNTg4MjpjN2E0YTY2MzUyN2MxNGYzY2UyMjdkYzk4M2IwZDVmMzI1ZjU5ZmQ1YmViMzM5M2Y0YTZhMGJlMjM1YjFkMjhl; sptg=%5B%5D; usprivacy=1---; cf_clearance=Mq4yVBqetsCOu4H0YV8K4sMU6iyHP_qwN8PyKzh1jgI-1762278924-1.2.1.1-O0RibhNkp7Mi3dG19p8AiDK3b8zcg9frC391tUuPpz6UYexUIB_Z5nIrPLfygSHZUJH0CMCYroqGgC8iEZu0J0XiDkfQEtrlffL8Eh9HEM5Ve_bYO3F9SR9ZyHKheHwcZbP_8CaQI_Wiz2fcGcw3GmKOlvNPufqgJI8elLmQ1ktPahA8jTfmUnizDTk4m5A_QjFYaKmf8IBZqoyGWAQBQZgKCBPsuVvaCz.1dbbIJcU; OptanonConsent=isGpcEnabled=1&datestamp=Thu+Nov+06+2025+13%3A49%3A23+GMT%2B0000+(Greenwich+Mean+Time)&version=202505.1.0&hosts=&landingPath=NotLandingPage&consentId=0536c801-f1f7-4e04-a033-afd53266369a&interactionCount=1&groups=V2STACK42%3A0%2CC0005%3A0%2CC0004%3A0%2CC0001%3A1%2CC0003%3A0%2CC0002%3A0&isIABGlobal=false&geolocation=GB%3BSCT&isAnonUser=1&AwaitingReconsent=false; OneTrustWPCCPAGoogleOptOut=true; OptanonAlertBoxClosed=2025-11-04T14:39:00.778Z; eupubconsent-v2=CQaXJQAQaXJQAAcABBENCDFgAAAAAAAAACiQAAAW8gIAA4AGaAZ8BKoDtgJRgTJAosBRwCqQFWQKwAVzAr6BasC3gAAA.YAAAAAAAAAAA; wikia_beacon_id=qiR3dts87t; _b2=-Qd7XR9hK6.1762267140864; wikia_session_id=IAE0q00xmI; xcr=gb; satcv=c3e8529e934285546037402a9ad44869; Geo={%22region%22:%22EDH%22%2C%22city%22:%22edinburgh%22%2C%22country_name%22:%22united kingdom%22%2C%22country%22:%22GB%22%2C%22continent%22:%22EU%22}; sessionId=e457d3fe-960f-421d-9498-81aab2bbb73d; pvNumber=2; pvNumberGlobal=2',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
        'TE': 'trailers',
        'default-src':'self'
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(req)
    data = response.json()
    
    #print(response, file=sys.stderr)
    return data