from flask import Flask, render_template, request, redirect, session, url_for
import json
import requests
import sys
import datetime
import ast
import bcrypt
from datetime import timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key='SecretKey'

valid_email='person@napier.ac.uk'
valid_pwhash=bcrypt.hashpw('comic'.encode('utf-8'), bcrypt.gensalt())

def retrievePublisherVolumes():
    # Codes:
        # 31 - Marvel
        # 10 - DC
    publishers = [31, 10]
    publisherDict=dict()
    
    # Goes through each publisher and retrieves all of their volumes.
        # Assigns each of those volume ids as a key in the dict indicating the publisher.
        # This information can be used to check the publisher of each issue in their volume sections (since this is the only publisher specific information available)
        # By making this a key in a dict, the look-up process is much faster which is important given that Marvel alone has upwards of 13,000 volumes to consider.
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

#Calls retrievePublisherVolumes once on starting the server.
publisherDict = retrievePublisherVolumes()

def requires_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        status=session.get('logged_in', False)
        if not status:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/logout/')
def logout():
    session['logged_in'] = False
    return redirect(url_for('root'))
    
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        user=request.form['email']
        pw=request.form['password']
        
        if check_auth(request.form['email'], request.form['password']):
            session['logged_in'] = True
            return redirect(url_for('homepage'))
    
    return render_template('login.html')
    
def check_auth(email, password):
    if email==valid_email and valid_pwhash == bcrypt.hashpw(password.encode('utf-8'), valid_pwhash):
            return True
    return False

@app.route('/')
def root():
    #On load retrieves the comic to be displayed on the index.
    return render_template('index.html', comic=retrieveIndexData())
    
@app.route('/homepage/')
@requires_login
def homepage():
    return render_template('homepage.html')
    
@app.route('/collection/')
@requires_login
def collection():
    return render_template('collection.html')
    
@app.route('/specific_book/')
@requires_login
def specific_book():
    #Receives the comic sent to it via search/collection/weekly
    postedComic = request.args.get('comic', None)
    
    if(postedComic is None): 
        return redirect(url_for('homepage'))
        
    #Evaluates it into a dictionary since the specific data structure is lost on POSTing.
    comic=ast.literal_eval(postedComic)
    
    return render_template('specific_book.html', comic=comic)
    
@app.route('/weekly/')
@requires_login
def weekly():
    #By default the weekly page starts on today's date.
    dates = [datetime.date.today()-timedelta(days=6), datetime.date.today()]
    
    #weekly calls the retrieveIssuesByDateWeekly to collect all of the issues in a given week in an API call.
    return render_template('weekly.html', comics=retrieveIssuesByDateWeekly(dates[1], 0), dates = dates)

@app.route('/search/')
@requires_login
def search():
    return render_template('search.html', comic=retrieveIndexData())

@app.route('/other_collection/')
@requires_login
def other_collection():
    return render_template('other_collection.html')
    
@app.route('/create_account/')
def create_account():
    return render_template('create_account.html')

def retrieveIssuesByDateWeekly(endDate, offset):
    url = "https://comicvine.gamespot.com/api/issues/"
    api_key = "2b739459da8dc4ec62f68656b642554dea026eca"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    #Filters down to the endDate minus 6 so it doesn't cover a whole week. Ex. Thursday<Day<=Thursday
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
    # Goes through the publisherDict to compare the volume ids and filter out any rejected comics.
    for x in data['results']:
        if x['volume']['id'] in publisherDict:
            filteredData.append(x)
    # If the results are greater than 100 then every issue in a given week may not be covered.
    # As such, it polymorphically loops through retrieving issues until all issues have been collected.
    if len(data['results']) == 100:
        filteredData= filteredData + retrieveIssuesByDateWeekly(endDate, offset+100)
    
    return filteredData



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
    
