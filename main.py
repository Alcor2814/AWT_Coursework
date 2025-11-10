from flask import Flask, render_template
import json
app = Flask(__name__)

@app.route('/')
def root():
    retrieveData()
    return render_template('index.html', comic=retrieveData())

@app.route('/login/')
def login():
    return render_template('login.html')
    
@app.route('/homepage/')
def homepage():
    return render_template('homepage.html')
    
@app.route('/collection/')
def collection():
    return render_template('collection.html')
    
@app.route('/specific_book/')
def specific_book():
    return render_template('specific-book.html')

import requests
import sys

def retrieveData():
    url = "https://comicvine.gamespot.com/api/"
    api_key = "2b739459da8dc4ec62f68656b642554dea026eca"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    req = url +"issues/?api_key=" + api_key + "&format=json&filter=volume:91078&sort=cover_date:desc"
    
    session = requests.Session()
    session.headers = headers
    response = session.get(req)
    data = response.json()
    
    cover = data['results'][0]['image']['small_url']
    volumeName = data['results'][0]['volume']['name']
    issueName = data['results'][0]['name']
    name = volumeName + " - " + issueName
    
    comic = [cover, name]
    #print(response, file=sys.stderr)
    #print(req, file=sys.stderr)
    return comic