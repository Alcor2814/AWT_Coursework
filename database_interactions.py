import configparser
import logging
import sqlite3
import bcrypt
import ast
import re

from logging.handlers import RotatingFileHandler
from flask import Flask, g, session

db_location='var/database.db'

def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = sqlite3.connect(db_location)
        g.db = db
    return db

def init_db(app):
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode = 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        
def check_auth(app, email, password):
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

def create_account_database(app, email, username, password):
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
        return True
    else:
        app.logger.warning("User attempted to create account using existing email: " + email)
    return False

def delete_account_from_database(app):
    # Deletes the session's account from the database.
    app.logger.warning("Deleting user " + session['name'] + " from database.")
    delete_collection_from_database(app)
    
    db = get_db()
    sql = f'DELETE FROM users WHERE UserEmail = {session['name']}'
    db.cursor().execute(sql)
    db.commit()

def delete_collection_from_database(app):
    app.logger.warning("Deleting user " + session['name'] + "'s collection from database.")
    db = get_db()
    sql = f'DELETE FROM collections WHERE UserEmail={session['name']}'
    db.cursor().execute(sql)
    db.commit()
        
def retrieve_collection(app, user):
    app.logger.info("Retrieving " + str(user) + " collection.")
    db = get_db()
    sql = f'SELECT * FROM collections WHERE UserEmail="{user}"'
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
        
    return collection

# Makes no distinction on user because users can only manage their own collections.
def add_to_collection_database(app, comic):
    if (check_comic_in_collection(app, comic['id']) is False):
        if (check_comic_in_database(app, comic['id']) is False):
            add_comic_to_database(app, comic)
        
        db = get_db()
        userEmail = session['name']
        sql = f'INSERT INTO collections VALUES ("{session['name']}", "{comic['id']}", "", "")'
        app.logger.info("Adding comic to user collection: " + str(comic['id']))
        db.cursor().execute(sql)
        db.commit()
    else:
        app.logger.info("User attempted to add already present comic to their collection: " + session['name'])
        
    return 0
    
# Makes no distinction on user because users can only manage their own collections.
def remove_from_collection_database(app, comicId):
    db = get_db()
    userEmail = session['name']
    sql = f'DELETE FROM collections WHERE UserEmail ="{userEmail}" AND ComicId="{comicId}"'
    app.logger.warning("Deleting comic " + comicId + "from user " + userEmail + " collection")
    db.cursor().execute(sql)
    db.commit()
    
    return 0
    
def check_comic_in_database(app, comicId):
    db = get_db()
    #Retrieves the comic to check if it exists.
    sql = f'SELECT * FROM comics WHERE id="{comicId}"'
    app.logger.info("Checking if comic exists: " + str(comicId))
    result = db.cursor().execute(sql).fetchall()
    
    if(not result):
        return False
    else:
        return True
        
def add_comic_to_database(app, comic):
    db = get_db()
    app.logger.info("Adding comic to database: " + str(comic['id']))
    if(comic['description'] is not None):
        # The use of " can break the statement below.
            # Uses are limited but should be handled.
        comic['description'] = re.sub(r'"', "'", comic['description'])
    sql = f'INSERT INTO comics VALUES ("{comic['id']}", "{comic['name']}", "{comic['store_date']}", "{comic['image']}", "{comic['issue_number']}", "{comic['description']}", "{comic['volume']}")'
    db.cursor().execute(sql)
    db.commit()
    return 0

def check_comic_in_collection(app, comicId):
    db = get_db()
    #Retrieves the comic to check if it exists.
    sql = f'SELECT * FROM collections WHERE UserEmail="{session['name']}" AND ComicId="{comicId}"'
    app.logger.info("Checking if comic is in user collection: " + str(comicId))
    result = db.cursor().execute(sql).fetchall()
    
    if(not result):
        return False
    else:
        return True

def retrieve_comic_reviews(app, comicId):
    if(check_comic_in_database(app, comicId)):
        db = get_db()
        app.logger.info("Retrieving reviews for comic: " + str(comicId))
        sql = f'SELECT UserEmail, ComicReview, DisplayReview FROM collections WHERE ComicId = {comicId} AND ComicReview <> ""'
        result = db.cursor().execute(sql).fetchall()
        resultPlusUsername = []
        
        if result is not None:
            for row in result:
                resultPlusUsername.append(row + retrieve_username_by_email(app, row[0]))
        return resultPlusUsername
    return []

def retrieve_user_review(app, comicId):
    app.logger.info("Retrieving user " + session['name'] + "'s review for " + str(comicId))
    db = get_db()
    sql = f"SELECT ComicReview FROM collections WHERE ComicId = {comicId} AND UserEmail = '{session['name']}'"
    # User reviews overwrite instead of stack so only one should be possible.
    result = db.cursor().execute(sql).fetchone()
    if result is not None:
        result = result[0]
    return result
    
def add_review_to_comic(app, review, comicId, displayReview):
    app.logger.info("Adding review to comic " + str(comicId))
    db = get_db()
    sql = f"UPDATE collections SET ComicReview='{review}', DisplayReview={displayReview} WHERE ComicId = {comicId} AND UserEmail = '{session['name']}'"
    app.logger.warning("Adding review to comic statement: " + sql)
    db.cursor().execute(sql)
    db.commit()
    return 0
        
def retrieve_user_list(app):
    db = get_db()
    #Retrieves the username and email.
        # Does not retrieve password as this is not needed.
    sql = f'SELECT UserName, UserEmail FROM users'
    app.logger.info("Retrieving all users for display")
    result = db.cursor().execute(sql).fetchall()
    
    return result

def retrieve_username_by_email(app, userEmail):
    db = get_db()
    sql = f'SELECT UserName FROM users WHERE UserEmail="{userEmail}"'
    # Each email can only have one username.
    result = db.cursor().execute(sql).fetchone()
    app.logger.info("Retrieved " + userEmail + " username: " + result[0])
    
    return result
