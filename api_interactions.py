import requests
import random
import datetime
import json
import configparser

from datetime import timedelta
from flask import Flask, session

publisherDict = dict()
    
def retrievePublisherVolumes(app):
    app.logger.info("Retrieving publishers.")

    # Codes:
        # 31 - Marvel
        # 10 - DC
    publishers = [31, 10]
    
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
                    publisherDict.update({x['id'] : ["Marvel", x['name']]})
                if p == publishers[1]:
                    publisherDict.update({x['id'] : ["DC Comics", x['name']]})
        except:
            app.logger.error("Publisher "+ str(p) + "failed to retrieve.")
    
    return publisherDict

def retrieveIssuesByDateWeekly(app, endDate, offset):
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
    # As such, it recursively loops through retrieving issues until all issues have been collected.
    if len(data['results']) == 100:
        filteredData= filteredData + retrieveIssuesByDateWeekly(app, endDate, offset+100)
    
    return filteredData

def findMatchingValueInPublisherDict(app, search, publisherInclude):
    app.logger.info("Finding volumes matching " + search)
    matchingVolumes = []
    for volume in publisherDict.items():
        if search in volume[1][1]:
            for publisher in publisherInclude:
                if volume[1][0] == publisher:
                    matchingVolumes.append(volume)
    app.logger.info("Matches found: " + str(len(matchingVolumes)))
    return matchingVolumes
    
def retrieveIssuesByVolume(app, volume, offset):
    app.logger.info("Retrieving issues for volume " + str(volume[1][1]) + " with offset of " + str(offset))
    
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
    # The search function will operate on cover date.
        # Dates are less important when doing a generalised search, and many records don't have recorded store dates (which would have been preferred).
    params={
        "api_key" : api_key,
        "format" : "json",
        "filter" : f"volume:{volume[0]}",
        "sort" : "cover_date:asc",
        "offset" : offset
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(url, params=params)
    data = response.json()
    
    # Recursively searches through the volume.
        # If it were any more than one person (me) using this in any given hour I would add a limiter to how far offset it can become to limit API calls.
    if len(data['results']) == 100 :
        data['results'] = data['results'] + retrieveIssuesByVolume(app, volume, offset+100)['results']
    
    return data

def retrieveIndexData(app):
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
        "sort" : "store_date:asc",
    }
    
    session = requests.Session()
    session.headers = headers
    response = session.get(url, params=params)
    data = response.json()
    
    if len(data['results']) > 1:
        selectedIssue = random.randrange(0, len(data['results'])-1)
    else:
        selectedIssue = 0
    
    cover = data['results'][selectedIssue]['image']['small_url']
    volumeName = data['results'][selectedIssue]['volume']['name']
    issueNumber = data['results'][selectedIssue]['issue_number']
    issueName = data['results'][selectedIssue]['name']
    name = volumeName
    
    if issueNumber is not None:
        name += " " + issueNumber
    if issueName is not None:
        name += " - " + issueName
    comic = [cover, name]
    
    return comic