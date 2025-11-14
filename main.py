from flask import Flask, render_template, request
import json
import requests
import sys
import datetime
from datetime import timedelta
app = Flask(__name__)

@app.route('/')
def root():
    return render_template('index.html', comic=retrieveIndexData())

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
    comic = request.args.get('comic', None)
    return render_template('specific-book.html', comic=comic)
    
@app.route('/weekly/')
def weekly():
    dates = [datetime.date.today()-timedelta(days=6), datetime.date.today()]
    return render_template('weekly.html', comics=retrieveIssuesByDateWeekly(dates[1], 0), dates = dates)

@app.route('/search/')
def search():
    return render_template('search.html', comic=retrieveIndexData())

@app.route('/other_collection/')
def other_collection():
    return render_template('other-collection.html')
    
@app.route('/create_account/')
def create_account():
    return render_template('create-account.html')
    
@app.route('/test/')
def test_page():
    return render_template('test_page.html')



def retrieveIssuesByDateWeekly(endDate, offset):
    publisherDict = retrievePublisherVolumes()
    
    url = "https://comicvine.gamespot.com/api/issues/"
    api_key = "2b739459da8dc4ec62f68656b642554dea026eca"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    params={
        "api_key" : api_key,
        "format" : "json",
        "sort" : "cover_date:desc",
        "filter" : "store_date:" + str(endDate-timedelta(days=6)) + "|" + str(endDate),
        "offset" : offset
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(url, params=params)
    data = response.json()

    filteredData=[]
    for x in data['results']:
        if x['volume']['id'] in publisherDict:
            filteredData.append(x)
    print(response.request.url, file=sys.stderr)
    if len(data['results']) == 100:
        filteredData= filteredData + retrieveIssuesByDateWeekly(endDate, offset+100)
    
    return filteredData
    
def retrievePublisherVolumes():
    publishers = [31, 10]
    publisherDict=dict()
    
    for p in publishers:
        url = "https://comicvine.gamespot.com/api/publisher/" + str(p) + "/"
        api_key = "2b739459da8dc4ec62f68656b642554dea026eca"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
        }
        params={
            "api_key" : api_key,
            "format" : "json",
        }
        session = requests.Session()
        session.headers = headers
        response = session.get(url, params=params)
        data = response.json()

        for x in data['results']['volumes']:
            if p == publishers[0]:
                publisherDict.update({x['id'] : "Marvel"})
            if p == publishers[1]:
                publisherDict.update({x['id'] : "DC Comics"})
    
    return publisherDict



def retrieveIndexData():
    url = "https://comicvine.gamespot.com/api/issues/"
    api_key = "2b739459da8dc4ec62f68656b642554dea026eca"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    params={
        "api_key" : api_key,
        "format" : "json",
        "filter" : "volume:91078",
        "sort" : "store_date:desc",
        "limit" : 1
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(url, params=params)
    data = response.json()
    
    cover = data['results'][0]['image']['small_url']
    volumeName = data['results'][0]['volume']['name']
    issueNumber = data['results'][0]['issue_number']
    issueName = data['results'][0]['name']
    name = volumeName
    
    if issueNumber is not None:
        name += " " + issueNumber
    if issueName is not None:
        name += " - " + issueName
    comic = [cover, name]
    #print(response.request.url, file=sys.stderr)
    #print(request, file=sys.stderr)
    return comic