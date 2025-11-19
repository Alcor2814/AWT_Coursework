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

app = Flask(__name__)
app.secret_key = ""
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
    session['name'] = None
    return redirect(url_for('root'))
    
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        app.logger.info("Starting login attempt.")

        user=request.form['email']
        pw=request.form['password']
        
        if check_auth(request.form['email'], request.form['password']):
            session['logged_in'] = True
            session['name'] = user
            return redirect(url_for('homepage'))
    
    return render_template('login.html')
    
def check_auth(email, password):
    db = get_db()
    app.logger.info("Checking for matching emails: " + email)
    
    #Checks that the input email exists in the database
    sql = f'SELECT * FROM users WHERE UserEmail="{email}"'
    cursor = db.cursor().execute(sql)
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