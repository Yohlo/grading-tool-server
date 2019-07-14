from flask import Blueprint, jsonify, request, redirect, send_from_directory, send_file, Response
from datetime import date, datetime
from functools import reduce
from flask_cors import CORS
import requests
import shutil
import json
import git
import os

from . import SITE_URL, SERVER_URL, SILO_SERVER_URL, REPOS_DIR, INSTRUCTORS, SECRET_KEY
from . import db
from . import canvas

silo_headers = {"secret_key": SECRET_KEY}

app =  Blueprint('battles', __name__)
CORS(app, resources=r'/*', allow_headers='Content-Type')

#########################
#### User  Functions ####
#########################

## GET /student
# Gets details about student using the supplied GitHub access token
@app.route('/student')
def student():
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    return jsonify({
        'login': user['login'],
        'name': user['name'],
        'avatar_url': user['avatar_url'],
        'is_admin': is_admin(user['login'])
    })

@app.route('/standings')
def get_standings():
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    ##
    # Get a database connection
    ##
    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()

        if login not in [student['login_id'] for student in canvas.getStudents()]:
            if login not in [instructor['login_id'] for instructor in INSTRUCTORS]:
                return "Sorry, you don't seem to be an authorized user!", 401


        ##
        # return player JSON
        ##
        raw_players = db.getPlayers(c)
        players = [(getPlayerDict(c, player)) for player in raw_players]
        return jsonify(sorted(players, key=lambda p: p['record'][0] - p['record'][1], reverse=True))
        



@app.route('/player')
def get_player():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if the user isn't found it will initialize the player given that the user is on canvas
     - return the players info
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    ##
    # Get a database connection
    ##
    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

        ##
        # check if that player exists
        ##
        if not player:
            if login not in [student['login_id'] for student in canvas.getStudents()]:
                if login not in [instructor['login_id'] for instructor in INSTRUCTORS]:
                    ## Return a big fat not authorized ERROR!!
                    return "Sorry, you don't seem to be an authorized user!", 401
            ## Initialize player
            db.initPlayer(c, login)
            player = db.getPlayer(c, login)

        ##
        # return player JSON
        ##
        playerDict = getPlayerDict(c, player, self=True)
        if player[3]:
            matchups = getMatchups(c, login)
        else: matchups = []
    return jsonify({"player": playerDict, "matchups": matchups})

@app.route('/player/screenname', methods=['GET'])
def get_screenname():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if not, return an error.
     - return the players screenname
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

        ##
        # Check if player exists
        ##
        if not player:
            return "Player not found", 404
        
        ##
        # Set the screenname
        ##
        return jsonify(db.getScreenName(c, login))

@app.route('/player/screenname', methods=['POST'])
def set_screenname():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if not, return an error.
     - set the players screenname in the db
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

        ##
        # Check if player exists
        ##
        if not player:
            return "Player not found", 404
        
        ##
        # Set the screenname
        ##
        screenname = request.form.get('screenname')

        if db.getScreenName(c, login) == screenname:
            return "The given screenname is identical to the current one.", 300

        if db.updateScreenName(c, login, screenname):
            return jsonify(screenname)
        return "Error setting screenname", 500

@app.route('/player/matchups')
def get_matchups():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if not, return an error.
     - get a list of all matchups involving that player
     - return that list
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

        ##
        # check if that player exists
        ##
        if not player:
            return "Player not found", 404

        ##
        # return player JSON
        ##
        matchups = getMatchups(c, login)
    return jsonify(matchups)

@app.route('/matchups')
def get_all_matchups():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if not, return an error.
     - Confirm the user is an admin
     - get a list of all matchups
     - return that list
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

        ##
        # check if that player exists
        ##
        if not player:
            return "Player not found", 404
        if not is_admin(login):
            return "Not authorized", 400

        ##
        # return player JSON
        ##
        matchups = getAllMatchups(c)
    return jsonify(matchups)

@app.route('/player/enroll')
def enroll_current_comment():
    '''
    This function will: 
     - authenticate with github via the given access code,
     - attempt to retrieve the players info
     - if not, return an error.
     - make a call to silo git logic
     - returns either commit or error
    '''
    ##
    # Authenticate user
    ##
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    #return  "The deadline to enroll has passed.", 300

    if not is_admin(user['login']):
        return "Students can no longer enroll in the competition.", 300

    conn, c = db.getConnection()
    with conn:

        ##
        # Retrieve players info from db
        ##
        login = user['login'].lower()
        player = db.getPlayer(c, login)

    ##
    # check if that player exists
    ##
    if not player:
        return "Player not found", 404

    ##
    # Call silo server to deal with git stuff
    ##
    a = requests.get(f"{SILO_SERVER_URL}/{login}/enroll", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

#########################
### Utility Functions ###
#########################
def is_admin(login):
    for instructor in INSTRUCTORS:
        if instructor["login_id"] == login:
            return True
    return False

def matchupReducer(c, results, next, admin=False):
    for matchup in results:
        # check if the same players are playing
        if matchup['player_one']['id'] == next[1] and matchup['player_two']['id'] == next[2] and not matchup['matchup_id'] == next[0]:
            matchup['matches'][next[0]] = [getMatchDict(c, match) for match in db.getMatches(c, next[0])]
            return results
    results.append(getMatchupDict(c, next, matches=True, admin=admin))
    return results

def getMatchups(c, login):
    matchups = db.getMatchups(c, login)
    matchups = reduce(lambda res, next: matchupReducer(c, res, next), matchups, [])
    return matchups

def getAllMatchups(c):
    matchups = db.getAllMatchups(c)
    matchups = reduce(lambda res, next: matchupReducer(c, res, next, admin=True), matchups, [])
    return matchups

def reducer(res, next):
    for item in res:
        if item['type'] == next['type']:
            item['ids'] = item['ids'] + next['ids']
            return res
    res.append(next)
    return res

def getPlayerDict(c, player, self=False):
    if self:
        return {
            'id': player[0],
            'screen_name': player[2],
            'enrolled_commit': player[3],
            'commit_comment': player[4],
            'record': db.getRecord(c, player[1]),
            'username': player[1]
        }
    return {
        'id': player[0],
        'screen_name': player[2],
        'record': db.getRecord(c, player[1])
    }

def getMatchupDict(c, matchup, matches=False, admin=False):
    if matches: 
        return {
            'matchup_id': matchup[0],
            'player_one': getPlayerDict(c, db.getPlayerById(c, matchup[1]), self=admin),
            'player_two': getPlayerDict(c, db.getPlayerById(c, matchup[2]), self=admin),
            'matches': {
                matchup[0]: [getMatchDict(c, match) for match in db.getMatches(c, matchup[0])]
            }
        }
    return {
        'matchup_id': matchup[0],
        'player_one': getPlayerDict(c, db.getPlayerById(c, matchup[1]), self=admin),
        'player_two': getPlayerDict(c, db.getPlayerById(c, matchup[2]), self=admin),
    }

def getMatchDict(c, match):
    return {
        'start_board': [int(move) for move in str(db.getStartTrace(c, match[1]))],
        'end_board_p1_starts': [int(move) for move in match[4]],
        'end_board_p2_starts': [int(move) for move in match[5]],
        'status': match[3]
    }
