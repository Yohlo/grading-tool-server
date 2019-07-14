import os
import datetime
import shutil

from flask import jsonify, request, send_from_directory, Blueprint
import json
import git

from . import REPOS_DIR, SECRET_KEY
from . import db

app =  Blueprint('battles', __name__)
app.secret_key = SECRET_KEY

@app.before_request
def authenticate():
    if request.headers['secret-key'] != app.secret_key:
        response = jsonify("Not authorized.")
        response.status_code = 401
        return response

def _clone_repo_reset(login):
    ''' Not as dangerous as it looks, but still pretty dangerous. '''
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/battles" % user_dir
    try:
        if os.path.isdir(repo_dir):
            shutil.rmtree(repo_dir)
    except Exception:
        # we no longer have control over this user's repository
        return None
    os.mkdir(repo_dir)
    try:
        repo = git.Repo.clone_from("git@github.iu.edu:csci-b351-sp19/%s-submission.git" % login, repo_dir)
        return repo
    except:
        return None

@app.route('/update_repo/<login>')
def update_repo(login):
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/battles" % user_dir
    
    if not os.path.isdir(user_dir):
        os.mkdir(user_dir)

    if os.path.isdir(repo_dir): # pull the repo if it exists
        try:
            repo = git.Repo(repo_dir, search_parent_directories=True)
            repo.git.reset('--hard')
            repo.git.clean('-fxd')
            repo.remotes.origin.pull()
        except:
            repo = _clone_repo_reset(login)
            if not repo:
                return 'Could not find repository.', 404
    else: # clone it using SSH if not (b351@silo ssh key is in my github account)
        repo = _clone_repo_reset(login)
        if not repo:
            return 'Could not find repository.', 404
    
    # get latest commit number
    try:
        commit = str(repo.head.commit)
    except:
        return 'Repository empty!', 404
    else:
        return jsonify(commit)

def _get_last_commit(login, retry=True):
    update_repo(login)
    
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/battles" % user_dir
    
    try:
        repo = git.Repo(repo_dir, search_parent_directories=True)
        head_commit = str(repo.head.commit)
    except:
        return {'commit_id': None,
                'commit_comment': None,
                'head_commit': None}
    
    if not os.path.isdir(f"{repo_dir}/a4"):
        return {'commit_id': None,
                'commit_comment': None,
                'head_commit': head_commit}
    try:
        ## a4 since this is the battles version ayooo
        assignment_id = "a4"
        commit = max(repo.iter_commits(paths=assignment_id), key=lambda c: c.authored_datetime)
    except:
        # we expect to have commits since we have the directory.
        # if we don't, something is up.
        if not retry:
            # this is a failure
            return {'commit_id': None,
                    'commit_comment': None,
                    'head_commit': None}
        repo.close()
        
        _clone_repo_reset(login)
        
        return _get_last_commit(login, retry=False)
    
    commit_id = str(commit)
    commit_comment = commit.message.strip()
    return {'commit_id': commit_id,
            'commit_comment': commit_comment,
            'head_commit': head_commit}

@app.route('<login>/get_last_commit')
def get_last_commit(login):
    return jsonify(_get_last_commit(login))

@app.route('/<login>/enroll')
def enroll(login):
    # return "Server down for maintainence.", 500
    previous_failed = False

    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/battles" % user_dir

    conn, c = db.getConnection()
    with conn:

        _commit = _get_last_commit(login)
        commit = _commit['commit_id']
        commit_comment = _commit['commit_comment']
        head_commit = _commit['head_commit']
        last_commit = db.getEnrolledCommit(c, login)[0]
        
        if not head_commit:
            return f"You haven't made any commits to your repository.", 404
        if not commit:
            return f"No files found in the a4 folder in your repository.", 404
        
        if not previous_failed and str(last_commit) == str(head_commit):
            return "You haven't pushed any commits since your last enrollment.", 300
        elif not previous_failed and str(last_commit) == str(commit):
            return f"None of your commits since your last enrollment have affected a4.", 300

        db.setEnrolledCommit(c, login, commit, commit_comment)
        db.resetPlayer(c, login)

    return jsonify({
        'enrolled_commit': commit,
        'commit_comment': commit_comment
    }), 200

#########################
#### Admin Functions ####
#########################
@app.route('/matchups/next')
def get_next_matchup():
    conn, c = db.getConnection()
    with conn:

        matchups = db.getAllMatchups(c, upcoming=True)
        if not matchups:
            print("No Matchups")
            return jsonify(False)

        matchup = matchups[0]
        matchupid = matchup[0]

        p1_username = db.getUsername(c, matchup[1])
        p2_username = db.getUsername(c, matchup[2])

    p1_folder = f"{REPOS_DIR}/{p1_username}/battles/a4"
    p2_folder = f"{REPOS_DIR}/{p2_username}/battles/a4"
    
    player_1_files = (open(p1_folder + "/player.py").read(), open(p1_folder + "/board.py").read())
    player_2_files = (open(p2_folder + "/player.py").read(), open(p2_folder + "/board.py").read())
    return jsonify((matchupid, player_1_files, player_2_files))

@app.route('/matchups/<matchup_id>/matches/next')
def get_next_match_from_matchup(matchup_id):
    conn, c = db.getConnection()
    with conn:

        matches = db.getMatches(c, matchup_id, upcoming=True)
        if not matches:
            return jsonify(False)
        match = matches[0]
        db.updateMatch(c, match[0], db.IN_PROGRESS, None, None)
        return jsonify({
            'match_id': match[0],
            'start_board': db.getStartTrace(c, match[1])
        })

@app.route('/matches/<match_id>/update', methods=["POST"])
def update_match(match_id):
    conn, c = db.getConnection()
    with conn:

        winner = int(request.values.get('winner'))
        if winner == 1: code = db.P1_WON
        elif winner == -1: code = db.P2_WON
        else: code = db.DRAW
        p1_0_trace = request.values.get('p1_O_trace')
        p2_0_trace = request.values.get('p2_O_trace')
        db.updateMatch(c, match_id, code, p1_0_trace, p2_0_trace)

    return jsonify("")