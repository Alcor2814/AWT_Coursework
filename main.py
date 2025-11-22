from flask import Flask, render_template, request, redirect, session, url_for, g
from datetime import timedelta
from functools import wraps
from logging.handlers import RotatingFileHandler

import json
import requests
import sys
import datetime
import ast
import bcrypt
import sqlite3
import configparser
import logging
import re
import random

app = Flask(__name__)
db_location='var/database.db'

def init(app):
    config = configparser.ConfigParser()
    try:
        config_location = "etc/defaults.cfg"
        config.read(config_location)
        
        app.config['DEBUG'] = config.get("config", "debug")
        app.config['ip_address'] = config.get("config", "ip_address")
        app.config['port'] = config.get("config", "port")
        app.config['url'] = config.get("config", "url")
        
        app.config['log_file'] = config.get("logging", "name")
        app.config['log_location'] = config.get("logging", "location")
        app.config['log_level'] = config.get("logging", "level")
        
        app.secret_key = config.get("session", "secret_key")
    except:
        app.logger.error("Could not read configs from: ", config_location)

def logs(app): 
    log_pathname = app.config['log_location'] + app.config['log_file']
    file_handler = RotatingFileHandler(log_pathname, maxBytes=1024*1024*10, backupCount=1024)
    file_handler.setLevel(app.config['log_level'])
    formatter = logging.Formatter("%(levelname)s | %(asctime)s | %(module)s | %(funcName)s | %(message)s")
    file_handler.setFormatter(formatter)
    app.logger.setLevel(app.config['log_level'])
    app.logger.addHandler(file_handler)
    
init(app)
logs(app)

def retrievePublisherVolumes():
    app.logger.info("Retrieving publishers.")

    # Codes:
        # 31 - Marvel
        # 10 - DC
    publishers = [31, 10]
    publisherDict=dict()
    
    # Goes through each publisher and retrieves all of their volumes.
        # Assigns each of those volume ids as a key in the dict indicating the publisher.
        # This information can be used to check the publisher of each issue in their volume sections (since this is the only publisher specific information available)
        # By making this a key in a dict, the look-up process is much faster which is important given that Marvel alone has upwards of 13,000 volumes to consider.
        # Time complexity O(1) for checking a volume in the dict.
        
    config = configparser.ConfigParser()
    try:
        config_location = "etc/defaults.cfg"
        config.read(config_location)
        api_key = config.get("query_parameters", "api_key")
    except:
        app.logger.error("Error retrieving API Key")
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    params={
        "api_key" : api_key,
        "format" : "json",
    }
    
    for p in publishers:
        url = "https://comicvine.gamespot.com/api/publisher/" + str(p) + "/"
        try:
            session = requests.Session()
            session.headers = headers
            response = session.get(url, params=params)
            data = response.json()

            for x in data['results']['volumes']:
                if p == publishers[0]:
                    publisherDict.update({x['id'] : "Marvel"})
                if p == publishers[1]:
                    publisherDict.update({x['id'] : "DC Comics"})
        except:
            app.logger.error("Publisher "+ p + "failed to retrieve.")
    
    return publisherDict

#Calls retrievePublisherVolumes on starting the server.
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
    app.logger.info("User "+ session['name'] + "logged out.")
    session['logged_in'] = False
    session['name'] = None

    return redirect(url_for('root'))
    
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        app.logger.info("Starting login attempt.")

        user=request.form['email']
        pw=request.form['password']
        
        if check_auth(request.form['email'], request.form['password']):
            #Clears password as soon as it is no longer needed.
            pw=""
            #Logs the user in.
            session['logged_in'] = True
            #Gives the session the user's email as a name so they can be given an experience unique to their account.
            session['name'] = user
            return redirect(url_for('homepage'))
    
    return render_template('login.html')
    
def check_auth(email, password):
    db = get_db()
    app.logger.info("Checking for matching emails: " + email)
    
    #Checks that the input email exists in the database
    sql = f'SELECT * FROM users WHERE UserEmail="{email}"'
    cursor = db.cursor().execute(sql)
    #Only one row should be possible to fetch, but the result needs to be limited to one row to be better operated upon.
    result = cursor.fetchone()
    
    if result:
        #Checks that the hashed password matches the stored hashed password
        if result[2].encode('utf-8') ==  bcrypt.hashpw(password.encode('utf-8'), result[2].encode('utf-8')):
            return True
            app.logger.info("User input password matched email: " + email)
        else:
            app.logger.warning("User input password did not match expected email: " + email)
    else:
        app.logger.info("User input email did not match expected database: " + email)
        
    return False

@app.route('/create_account/', methods=['GET', 'POST'])
def create_account():
    message=""
    if request.method=='POST':
        app.logger.info("Beginning account creation.")
        
        #Normalises so that all user emails are in lowercase and uppercase does not throw off checking for matching emails.
        email=request.form['email'].lower()
        username=request.form['username']
        #Immediately encrypts password to limit chance for leak.
        password=bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
        repeat_password=bcrypt.hashpw(request.form['repeat-password'].encode('utf-8'), password)
        
        #Checks that the password and repeated password match so the user definitely enters the right password.
        if password == repeat_password: 
            password=password.decode('utf-8')
            
            #Found an expected pattern for emails to verify the email structure.
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(pattern, email) is not None:
                try:
                    db = get_db()
                    
                    #Retrieves any User emails that match the input email to prevent creation of accounts using existing emails.
                    sql = f'SELECT * FROM users WHERE UserEmail="{email}"'
                    app.logger.info("Creation - Checking for matching emails: " + sql)
                    result = db.cursor().execute(sql).fetchall()
                    
                    if not result:
                        sql = f'INSERT INTO users VALUES ("{email}", "{username}", "{password}")'
                        db.cursor().execute(sql)
                        db.commit()
                        #Logs the user in.
                        session['logged_in'] = True
                        #Stores unique user information for retrieving unique experience.
                        session['name']=email
                       
                        app.logger.info("Added new account to the database: " + sql)
                        return redirect(url_for('homepage'))
                    else:
                        app.logger.warning("User attempted to create account using existing email: " + email)
                        message+="Email is already in use.\n" 
                except:
                    app.logger.error("Failed to connect to database.")
            else:
                app.logger.warning("User input email did not match expected pattern: " + email)
                message+="Email does not match expected pattern"
        else:
            app.logger.info("User passwords did not match")
            message+="Passwords do not match.\n"
                
    return render_template('create_account.html', message=message)

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
    db = get_db()
    sql = f'SELECT * FROM collections WHERE UserEmail="{session['name']}"'
    result = db.cursor().execute(sql)
    if (result is not None):
        findIds="("
        
        for row in result:
            findIds += '"' + str(row[1]) + '",'
        findIds = findIds.rstrip(',')
        findIds+= ")"
        
        sql = f'SELECT * FROM comics WHERE Id IN {findIds}'
        result = db.cursor().execute(sql)
        
        # Converts the retrieved database info into a dict that can be used by the collection page
        
        collection=[]
        for row in result:
            tempComic = {
                "id" : row[0],
                "name" : row[1],
                "store_date" : row[2],
                "image" : ast.literal_eval(row[3]),
                "issue_number" : row[4],
                "description" : row[5],
                "volume" : ast.literal_eval(row[6])
            }
            collection.append(tempComic)
    else:
        collection=[]
        
    return render_template('collection.html', collection = collection)
    
@app.route('/specific_book/')
@requires_login
def specific_book():
    #Receives the comic sent to it via search/collection/weekly
    sentComic = request.args.get('comic', None)
    
    if(sentComic is None): 
        return redirect(url_for('homepage'))
        
    #Evaluates it into a dictionary since the specific data structure is lost on POSTing.
    comic=ast.literal_eval(sentComic)
    #Removes html tags from description because it is unnecessary/shouldn't be implicitly trusted.
    if(comic['description'] is not None):
        comic['description'] = re.sub(r"<.*?>", " ", comic['description'])
    
    return render_template('specific_book.html', comic=comic)
   
@app.route('/add_to_collection/')
def add_to_collection():
    comic = request.args.get('comic', None)
    comic=ast.literal_eval(comic)
    
    if(comic is None):
        return redirect(url_for('homepage'))
    
    if (check_comic_in_collection(comic) is False):
        if (check_comic_in_database(comic) is False):
            add_comic_to_database(comic)
        
        db = get_db()
        userEmail = session['name']
        sql = f'INSERT INTO collections VALUES ("{session['name']}", "{comic['id']}", "", "")'
        app.logger.info("Adding comic to user collection: " + str(comic['id']))
        db.cursor().execute(sql)
        db.commit()
    else:
        app.logger.info("User attempted to add already present comic to their collection: " + session['name'])
    
    return redirect(url_for('specific_book', comic=comic))

@app.route('/remove_from_collection/')
def remove_from_collection():
    comicId = request.args.get('comicId', None)
    
    db = get_db()
    userEmail = session['name']
    sql = f'DELETE FROM collections WHERE UserEmail ="{userEmail}" AND ComicId="{comicId}"'
    app.logger.warning("Deleting comic " + comicId + "from user " + userEmail + " collection")
    db.cursor().execute(sql)
    db.commit()
    return redirect(url_for('collection'))
    
def check_comic_in_database(comic):
    db = get_db()
    #Retrieves the comic to check if it exists.
    sql = f'SELECT * FROM comics WHERE id="{comic['id']}"'
    app.logger.info("Checking if comic exists: " + str(comic['id']))
    result = db.cursor().execute(sql).fetchall()
    
    if(not result):
        return False
    else:
        return True

def add_comic_to_database(comic):
    db = get_db()
    app.logger.info("Adding comic to database: " + str(comic['id']))
    sql = f'INSERT INTO comics VALUES ("{comic['id']}", "{comic['name']}", "{comic['store_date']}", "{comic['image']}", "{comic['issue_number']}", "{comic['description']}", "{comic['volume']}")'
    db.cursor().execute(sql)
    db.commit()
    return 0

def check_comic_in_collection(comic):
    db = get_db()
    #Retrieves the comic to check if it exists.
    sql = f'SELECT * FROM collections WHERE UserEmail="{session['name']}" AND ComicId="{comic['id']}"'
    app.logger.info("Checking if comic is in user collection: " + str(comic['id']))
    result = db.cursor().execute(sql).fetchall()
    
    if(not result):
        return False
    else:
        return True
    
@app.route('/weekly/', methods=['GET', 'POST'])
@requires_login
def weekly():
    if request.method == 'GET':
        #By default the weekly page starts on today's date.
        dates = [datetime.date.today()-timedelta(days=6), datetime.date.today()]
        comics=retrieveIssuesByDateWeekly(dates[1], 0)
        #weekly calls the retrieveIssuesByDateWeekly to collect all of the issues in a given week in an API call.
        return render_template('weekly.html', comics=comics, dates=dates)
    elif request.method == 'POST':
        #Receives the sent date as a datetime
        date=datetime.datetime.strptime(request.form['calendar'], '%Y-%m-%d')
        #Converts to date - unsure how to make it just receive as date.
        date=date.date()
        
        app.logger.info("Received calendar date " + str(date))
        #Checks if the date received is greater than today. If yes, redirects to today.
            #The calendar can be limited via JavaScript Max, but this doesn't work on all browsers.
        if date > datetime.date.today():
            app.logger.info("User attempted to input date greater than today.")
            date=datetime.date.today()
        dates=[date-timedelta(days=6), date]
        comics = retrieveIssuesByDateWeekly(dates[1], 0)
        return render_template('weekly.html', comics=comics, dates=dates)

@app.route('/search/')
@requires_login
def search():
    return render_template('search.html', comic=retrieveIndexData())

@app.route('/other_collection/')
@requires_login
def other_collection():
    return render_template('other_collection.html')
    
def retrieveIssuesByDateWeekly(endDate, offset):
    app.logger.info("Retrieving issues for week ending " + str(endDate) + " with offset of " + str(offset))

    config = configparser.ConfigParser()
    try:
        config_location = "etc/defaults.cfg"
        config.read(config_location)
        api_key = config.get("query_parameters", "api_key")
    except:
        app.logger.error("Error retrieving API Key")
    
    url = "https://comicvine.gamespot.com/api/issues/"
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
    config = configparser.ConfigParser()
    try:
        config_location = "etc/defaults.cfg"
        config.read(config_location)
        api_key = config.get("query_parameters", "api_key")
    except:
        app.logger.error("Error retrieving API Key")
        
    url = "https://comicvine.gamespot.com/api/issues/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0',
    }
    selectedVolume = random.choice(list(publisherDict.keys()))
    params={
        "api_key" : api_key,
        "format" : "json",
        "filter" : f"volume:{selectedVolume}",
        "sort" : "store_date:desc",
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(url, params=params)
    data = response.json()
    
    selectedIssue = random.randrange(0, len(data['results']))
    
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
    
def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = sqlite3.connect(db_location)
        g.db = db
    return db

@app.teardown_appcontext
def close_db_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
        
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode = 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()