import sqlite3
import string
import random

"""  tournament.db
 ---------------     ---------------     ----------------    ----------------
| players       |   | boards        |   | matches        |  | matchups       |
| --------------|   | --------------|   | -------------- |  | -------------- |
| PK id         |   | PK id         |   | PK id          |  | PK id          |
| username      |   | startTrace    |   | FK boardId     |  | FK player1     |
| nickname      |    ---------------    | FK matchupId   |  | FK player2     |
|enrolled_commit|                       | status         |  | player1_commit |
|commit_comment |                       |endTraceP1Starts|  | player2_commit |
 ---------------                        |endTraceP2Starts|   ----------------
                                         ----------------
"""

from . import DB_FILE

# statuses of matches
IN_QUEUE = 0 # used to denote that a match is in queue
IN_PROGRESS = 1 # used to denote that a match is in progress
P1_WON = 2 # used to denote that the player 1 of a match has won
P2_WON = 3 # used to denote that the player 2 of a match has won
DRAW = 4 # used to denote that a match ended in a draw
CANCELLED = 5 # used to denote that a match was cancelled

def getConnection():
    """
    This function creates a db connection and returns that and the cursor.
    Returns:
        conn: the connection to the db _DB
        c:    the cursor
    """
    conn = sqlite3.connect(DB_FILE) # connect to our db
    c = conn.cursor()
    return conn, c

# courtesy of Stack Overflow
def _nickname_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def initPlayer(c, username):
    """
    This function initializes a player based on the given username. Assigns a random nickname.
    Parameters: 
        username (str): username of the player to initialize.
    Returns:
        This function does not return anything.
    """
    # creates a new player in the players table and assignes a random nickname
    c.execute("INSERT INTO players(username, nickname) VALUES (?, ?)", (username, _nickname_generator())) # insert a new player

def getPlayer(c, username):
    """
    This function gets the id of the given player.
    Parameters: 
        username (str): username of the player.
    Returns:
        int: id of the given player.
    """
    # grab the row of the player and fetchone, since there should only be one!
    row = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    return row

def getPlayers(c):
    """
    """
    row = c.execute("SELECT * FROM players WHERE enrolled_commit IS NOT NULL").fetchall()
    return row

def getPlayerById(c, id):
    """
    """
    # grab the row of the player and fetchone, since there should only be one!
    row = c.execute("SELECT * FROM players WHERE id=?", (str(id),)).fetchone()
    return row

def resetPlayer(c, username):
    """
    This function cancels all of a player's upcoming matches,
    and creates a new set of matchups for them.
    Parameters:
        username (str): username of the player to initialize.
    Returns:
        This function does not return anything.
    """
    ### This part cancels upcoming matches!
    upcoming_matchups = getMatchups(c, username, upcoming=True)
    for matchup in upcoming_matchups:
        matches = getMatches(c, matchup[0], upcoming=True)
        for match in matches:
            updateMatch(c, match[0], CANCELLED, None, None)
    # And creates new matchups
    createMatchups(c, username)

def getUsername(c, playerId):
    """
    This function gets the user name of the given player.
    Parameters: 
        playerId (int): id of the player.
    Returns:
        str: user name of the given player.
    """
    # grab the row of the player and fetchone, since there should only be one!
    row = c.execute("SELECT * FROM players WHERE id=?", (playerId,)).fetchone()
    return row[1] # [1] is the username

def getPlayerId(c, username):
    """
    This function gets the id of the given player.
    Parameters: 
        username (str): username of the player.
    Returns:
        int: id of the given player.
    """
    # grab the row of the player and fetchone, since there should only be one!
    row = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    return row[0] # [0] is the id

def getScreenName(c, username):
    """
    This function gets the sreen name of the given player.
    Parameters: 
        username (str): username of the player.
    Returns:
        str: screen name of the given player.
    """
    # grab the row of the player and fetchone, since there should only be one!
    row = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    return row[2] # [2] is the screenname

def updateScreenName(c, username, screenName):
    """
    This function sets the sreen name of the given player.
    Parameters: 
        username (str):   username of the player.
        screenName (str): screen name to set for the user
    Returns:
        bool: False if the screen name has already been taken, True otherwise.
    """
    row = c.execute("SELECT * FROM players WHERE nickname=?", (screenName,)).fetchone()
    if row: # screenName already taken!! 
        return False
    c.execute('''UPDATE players
            SET nickname=?
            WHERE username=?''', (screenName, username))
    return True # we were successfully able to update the screen name

def setEnrolledCommit(c, username, enrolled_commit, commit_comment):
    """
    This function sets the enrolled_commit of the given player.
    Parameters: 
        username (str):   username of the player.
        enrolled_commit (str): enrolled_commit to set for the user
    """
    row = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    c.execute('''UPDATE players
            SET enrolled_commit=?
            WHERE username=?''', (enrolled_commit, username))
    c.execute('''UPDATE players
            SET commit_comment=?
            WHERE username=?''', (commit_comment,  username))

def getEnrolledCommit(c, username):
    """
    This function gets the enrolled_commit of the given player.
    Parameters: 
        username (str):   username of the player.
    """
    row = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    return (row[3], row[4])

def getRecord(c, username):
    """
    This function gets the overall record of the given player.
    Parameters: 
        username (str):  username of the player.
    Returns:
        (int, int, int): overall record of the player in (w, l, d) format.
    """
    w, l, d = 0,0,0
    playerId = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()[0]
    matchups = c.execute("SELECT * FROM matchups WHERE player1=? OR player2=?", (playerId, playerId,)).fetchall()
    for matchup in matchups: # iterate through all matchups associated with our player.
        # grabs the most recent matchup (one with the highest matchup id)
        most_recent = c.execute("SELECT * FROM matchups WHERE player1=? AND player2=? ORDER BY id desc", (matchup[1], matchup[2],)).fetchone()

        if matchup != most_recent:
            continue

        # grabs all of the matches associated with the most recent matchup id
        matches = c.execute("SELECT * FROM matches WHERE matchupId=?", (most_recent[0],)).fetchall()
        # determines if our player is player one or not
        isPlayerOne = (most_recent[1] == playerId)
        match_w, match_l, match_d = 0,0,0
        for match in matches: # iterate through all of the matches
            # check if the cases for a win for our player are true
            if (match[3] == P1_WON and isPlayerOne) or (match[3] == P2_WON and not isPlayerOne):
                match_w+=1
            # check if the cases for a loss for our player are true
            elif (match[3] == P2_WON and isPlayerOne) or (match[3] == P1_WON and not isPlayerOne):
                match_l+=1
            # determine if it was a draw
            elif match[3] == DRAW:
                match_d+=1
            # this else is unneeded - but i wanted to point out that any other case means that the match
            # is still either in the queue or in progress.
            else:
                pass
        
        # if our match wins is equal to our match loss, then it was a draw.
        if (match_w == match_l != 0) or match_d == len(matches):
            d+=1
        # if we won more than we lost, then we won overall.
        elif match_w > match_l:
            w+=1
        # if we won less than we lost, then we lost overall.
        elif match_w < match_l:
            l+=1
    # finally, return the totals of our record.
    return w,l,d

def createMatchups(c, username):
    """
    This function creates all possible matchups and matches for the given player.
    Parameters: 
        username (str): username of the player.
    Returns:
        This function does not return anything.
    """
    # grab our player and player id
    player = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()
    playerId = player[0]
    # grab all of our opponenets -- everyone that isn't us!
    opponents = c.execute("SELECT * FROM players WHERE id!=? and enrolled_commit IS NOT NULL", (playerId,)).fetchall()
    # grab all of the boards we have to play on
    boards = c.execute("SELECT * FROM boards").fetchall()
    for opponent in opponents: # iterate through our opponents
        print(opponent)
        player2 = opponent[0] # get the id of the current opponent
        # create the matchup in the matchups table. set player1 to whomever has the lowest id
        c.execute("INSERT INTO matchups(player1, player2, player1_commit, player2_commit) VALUES (?, ?, ?, ?)", \
            (playerId if playerId < player2 else player2, playerId if playerId > player2 else player2, 
            player[3] if playerId < player2 else opponent[3], player[3] if playerId > player2 else opponent[3]))
        # get the id of the matchup we just created
        matchupId = c.lastrowid
        for board in boards: # iterate through our boards
            # create the specific matches using our new matchup id and set the status to IN_QUEUE
            c.execute("INSERT INTO matches(boardId, matchupId, status) VALUES (?, ?, ?)", (board[0], matchupId, IN_QUEUE))

def getMatchups(c, username, upcoming=False):
    """
    This function gets all the matchups associated with the given player.
    Parameters: 
        username (str): username of the player.
    Returns:
        listof(matchups): The list of all matchup entities in the db for the given player. 
                          Refer to db diagram above for structure and value orders.
    """
    # grab our player id
    playerId = c.execute("SELECT * FROM players WHERE username=?", (username,)).fetchone()[0]
    # grab all of the matches associated with our player id
    matchups = c.execute("SELECT * FROM matchups WHERE player1=? OR player2=?", (playerId, playerId,)).fetchall()
    if upcoming: # if we want to filter to only upcoming matchups
        upcoming_matchups = []
        for matchup in matchups: # check every matchup for inprogress matches
            if c.execute("SELECT * FROM matches WHERE matchupId=? AND (status=? OR status=?)", \
                                            (matchup[0], IN_PROGRESS, IN_QUEUE,)).fetchall():
                upcoming_matchups.append(matchup)
        return upcoming_matchups
    return matchups

def getMatchupById(c, id):
    """
    """
    matchup = c.execute("SELECT * FROM matchups WHERE id=?", (str(id),)).fetchone()
    return matchup

def getAllMatchups(c, upcoming=False):
    """
    This function gets all matchups. if upcoming is set to true, it only returns matches
    where the status is IN_QUEUE
    Parameters: 
        upcoming (bool): whether or not to limit matchups with IN_QUEUE matches.
    Returns:
        listof(matchups): The list of all matchups.
    """
    # grab all of the matches
    matchups = c.execute("SELECT * FROM matchups").fetchall()
    if upcoming:
        upcoming_matchups = []
        for matchup in matchups:
            if c.execute("SELECT * FROM matches WHERE matchupId=? AND status=?", \
                                            (matchup[0], IN_QUEUE,)).fetchall():
                upcoming_matchups.append(matchup)
        return upcoming_matchups
    return matchups

### TODO ###
def cleanupOldMatches():
    """
    This function finds all superceded matchups and deletes
    them and all of the matches associated with them.
    Returns:
        This function does not return anything.
    """
    # looking for matchups
    # where there are newer matchups with the exact same players
    # then delete those matchups and any matches with that matchup id
    pass

def getMatches(c, matchupId, upcoming=False, notCancelled=False):
    """
    This function gets all the matches associated with the given matchup.
    Parameters: 
        matchupId (int): id of the matchup
    Returns:
        listof(matches): The list of all matches entities in the db for the given matchup. 
                          Refer to db diagram above for structure and value orders.
    """
    # grab all of the matches associated with our matchupId
    matches = c.execute("SELECT * FROM matches WHERE matchupId=?", (matchupId,)).fetchall()
    if upcoming:
        upcoming_matches = []
        for match in matches:
            if match[3] == IN_QUEUE:
                upcoming_matches.append(match)
        return upcoming_matches
    if notCancelled:
        actual_matches = []
        for match in matches:
            if match[3] != CANCELLED:
                actual_matches.append(match)
        return actual_matches
    return matches

def updateMatch(c, matchId, result, endTraceP1Starts, endTraceP2Starts):
    """
    This function updates the given match based on given params.
    Parameters: 
        matchId (int): id of the match
        result  (int): result of the match. must be one of:
                        IN_QUEUE, IN_PROGRESS, P1_WON, P2_WON, DRAW
                        enums located at top of file.
        endTraceP1Starts (int): Trace of the final board when p1 starts as 'O'
        endTraceP2Starts (int): Trace of the final board when p2 starts as 'O'
    Returns:
        This function does not return anything.
    """
    # update our match based on the params
    c.execute('''UPDATE matches
            SET status=?, 
            endTraceP1Starts=?,
            endTraceP2Starts=?
            WHERE id=?''', (result, str(endTraceP1Starts) if endTraceP1Starts else '', str(endTraceP2Starts) if endTraceP2Starts else '', matchId))

def getStartTrace(c, boardId):
    return c.execute("SELECT * FROM boards WHERE id=?", (str(boardId),)).fetchone()[1]

def _addBoard(boardTrace):
    """
    This function adds a given board based on trace to the boards table.
    Parameters: 
        boardTrace (int): trace of the board to add
    Returns:
        This function does not return anything.
    """
    conn, c = getConnection()
    with conn:
        # insert the new board
        c.execute("INSERT INTO boards(startTrace) VALUES (?)", (boardTrace,))

def getData():
    conn, c = getConnection()
    with conn:

        def getPlayerDict(c, player):
            return {
                'id': player[0],
                'screen_name': player[2],
                'enrolled_commit': player[3],
                'commit_comment': player[4],
                'record': getRecord(c, player[1]),
                'username': player[1]
            }

        raw_players = getPlayers(c)
        players = [(getPlayerDict(c, player)) for player in raw_players]
        sorted_players = sorted(players, key=lambda p: p['record'][0] - p['record'][1], reverse=True)

        print(len(sorted_players))

        top_ten = sorted_players[0:10]

        top_ten_ids = [p['id'] for p in top_ten]

        ## Get the number of matchups
        raw_matchups = getAllMatchups(c)
        print(raw_matchups)
        matchups = list(set(raw_matchups))

        matchups = list(filter(lambda m: (m[1] in top_ten_ids and m[2] in top_ten_ids), matchups))

        print(f"# of mathups: {len(matchups)}")

        ## Get the number of matches
        matches = []
        for matchup in matchups:
            matches += getMatches(c, matchup[0], notCancelled=True)
        print(f"# of matches: {len(matches)}")

        ## Get the number of games
        print(f"# of games: {len(matches) * 2}")

        ## Get the moves!
        boards = ["", "2414", "265333365326", "16325633311", "24141103244"]

        moves = [0 for i in range(7)]
        for match in matches:
            g1_trace = match[4][len(boards[match[1]-1]):]
            g2_trace = match[5][len(boards[match[1]-1]):]

            for move in g1_trace:
                if int(move) == 9: continue
                moves[int(move)] += 1
            for move in g2_trace:
                if int(move) == 9: continue
                moves[int(move)] += 1

        print(moves)
        for i in range(len(moves)):
            print(f"{i}: {moves[i]}")
        print(f"# of moves: {sum(moves)}")



def initDatabase():
    """
    This function initializes the db from scratch. Useful when testing.
    Returns:
        This function does not return anything.
    """
    conn, c = getConnection()
    with conn:
        c.execute("DROP TABLE IF EXISTS matchups")
        c.execute("DROP TABLE IF EXISTS matches")
        c.execute("DROP TABLE IF EXISTS players")
        c.execute("DROP TABLE IF EXISTS boards")
        c.execute("CREATE TABLE players (id integer PRIMARY KEY, username text, nickname text, enrolled_commit text, commit_comment text)")
        c.execute("CREATE TABLE boards (id integer PRIMARY KEY, startTrace integer)")
        c.execute("CREATE TABLE matchups (id integer PRIMARY KEY, " +
                    "player1 integer, player2 integer, " +
                    "player1_commit text, player2_commit text," +
                    "FOREIGN KEY(player1) REFERENCES players(id), " +
                    "FOREIGN KEY(player2) REFERENCES players(id))")
        c.execute("CREATE TABLE matches (id integer PRIMARY KEY, boardId integer, " +
                    "matchupId integer, status integer, " +
                    "endTraceP1Starts text DEFAULT \"\" NOT NULL, endTraceP2Starts text DEFAULT \"\" NOT NULL, " +
                    "FOREIGN KEY(boardId) REFERENCES boards(id), " +
                    "FOREIGN KEY(matchupId) REFERENCES matchups(id))")
    
    for board in ["", "2414", "265333365326", "16325633311", "24141103244"]: #"6", "33", "244613", "355553334130"]:
        _addBoard(board)

def printTable(table): 
    """
    This function is used to print a given table out row by row. Useful when testing.
    Returns:
        This function does not return anything.
    """
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    with conn:
        cur.execute("SELECT * FROM %s" % table)
        print("==========%s==========" % table)
        for row in cur.fetchall():
            print(row)

if __name__ == "__main__":
    # Print out all of the table values
    ###################################
    _printTable("players")
    _printTable("boards")
    _printTable("matchups")
    _printTable("matches")
