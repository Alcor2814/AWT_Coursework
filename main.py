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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(req)
    data = response.json()
    
    #print(response, file=sys.stderr)
    return data