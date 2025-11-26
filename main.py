import re
import datetime

from flask import Flask, render_template, request, redirect, session, url_for
from datetime import timedelta
from functools import wraps

import api_interactions
import database_interactions
import logging_setup
from logging_setup import *
from api_interactions import *
from database_interactions import *

app = Flask(__name__)
    
init(app)
logs(app)

#Calls retrievePublisherVolumes on starting the server.
retrievePublisherVolumes(app)

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
    app.logger.info("User "+ session['name'] + " logged out.")
    session['logged_in'] = False
    session['name'] = None

    return redirect(url_for('root'))
    
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        app.logger.info("Starting login attempt.")

        user=request.form['email']
        pw=request.form['password']
        
        if check_auth(user, pw):
            #Clears password as soon as it is no longer needed.
            pw=""
            #Logs the user in.
            session['logged_in'] = True
            #Gives the session the user's email as a name so they can be given an experience unique to their account.
            session['name'] = user
            return redirect(url_for('homepage'))
    return render_template('login.html')
    
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
                create_account_database(app, email, username, password)
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
    return render_template('index.html', comic=retrieveIndexData(app))
    
@app.route('/homepage/')
@requires_login
def homepage():
    users = retrieve_user_list(app)
    return render_template('homepage.html', users=users)

@app.route('/collection/')
@requires_login
def collection():
    collection = retrieve_collection(app, session['name'])
    return render_template('collection.html', collection = collection)

@app.route('/other_collection/', methods=['POST'])
@requires_login
def other_collection():
    user= request.form['user']
    user = ast.literal_eval(user)
    collection = retrieve_collection(app, user[1])
    return render_template("other_collection.html", collection=collection, user=user[0])
    
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
    
    return render_template('specific_book.html', comic=comic, renderAdd= not check_comic_in_collection(app, comic))
   
@app.route('/add_to_collection/')
def add_to_collection():
    comic = request.args.get('comic', None)
    # Evaluates the comic because dict type is lost in transit.
    try:
        comic=ast.literal_eval(comic)
    except:
        return redirect(url_for('homepage'))
    
    add_to_collection_database(comic)
    return redirect(url_for('specific_book', comic=comic))

@app.route('/remove_from_collection/')
def remove_from_collection():
    comicId = request.args.get('comicId', None)
    
    remove_from_collection_database(comicId)
    return redirect(url_for('collection'))
    
@app.route('/weekly/', methods=['GET', 'POST'])
@requires_login
def weekly():
    if request.method == 'GET':
        #By default the weekly page starts on today's date.
        dates = [datetime.date.today()-timedelta(days=6), datetime.date.today()]
        comics=retrieveIssuesByDateWeekly(app, dates[1], 0)
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
        comics = retrieveIssuesByDateWeekly(app, dates[1], 0)
        return render_template('weekly.html', comics=comics, dates=dates)

@app.route('/search/', methods=['GET', 'POST'])
@requires_login
def search():
    if request.method == 'GET':
        return render_template('search.html', comics=[], suggestions=[])
    elif request.method == 'POST':
        try:
            search = request.form['search']
            suggestions = findMatchingValueInPublisherDict(app, search)
            comics=[]
        except:
            try:
                # Turns the returned string into a dict
                volume = eval(request.form['volume'])
                app.logger.info("Volume Selected: " + str(volume))
                suggestions=[]
                comics = retrieveIssuesByVolume(app, volume, 0)['results']
                app.logger.info("Retrieved " + str(len(comics)) + " issues.")
            except:
                app.logger.error("Unable to interpret string or volume")
            
    return render_template('search.html', comics=comics, suggestions=suggestions)
    
@app.teardown_appcontext
def close_db_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()