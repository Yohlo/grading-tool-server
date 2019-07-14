import os
import datetime
import shutil

from flask import jsonify, request, send_from_directory, Blueprint
from rq import Queue, Connection
from rq.job import Job
import json
import git

from . import REPOS_DIR, INSTRUCTORS, ASSIGNMENTS, GRADING_TOOLS_DIR, SECRET_KEY
from .worker import conn, runTest, runGrade
from . import database as db

app =  Blueprint('grading-tool', __name__)
app.secret_key = SECRET_KEY
q = Queue(connection=conn, default_timeout=600)

@app.before_request
def authenticate():
    if request.headers['secret-key'] != app.secret_key:
        response = jsonify("Not authorized.")
        response.status_code = 401
        return response

@app.route('/check/<job_id>/position')
def position(job_id):
    try:
        job = Job.fetch(job_id, connection=conn)
    except:
        job = None
    if not job: return ("No job", 404)
    if job.is_failed: return ("Job failed", 500)
    jobs = q.get_jobs() # seems not to include currently running job.
    if not jobs:
        return jsonify(0)
    try:
        return jsonify(jobs.index(job)+1)
    except ValueError:
        return jsonify(0)

@app.route('/check/<job_id>')
def fetch(job_id):
    try:
        job = Job.fetch(job_id, connection=conn)
    except:
        return "No job", 404
    return jsonify(job.is_finished)

@app.route('/enqueue_test', methods=['POST'])
def enqueue_test():
    data = request.get_json()
    job = q.enqueue_call(
        func=runTest, args=(request.values.get('assignment_id'), request.values.get('submission_dir'), request.values.get('output_file'),), result_ttl=86400
    )
    return jsonify(job.get_id()) if job else ("Error", 500)

@app.route('/qcount')
def q_count():
    return jsonify(q.count)

@app.route('/assignments/<assignment_id>/<login>/info')
def assignment_info(assignment_id, login):
    student_id = db.getStudentID(login.lower())
    
    try: assignment = db.getAssignment(ASSIGNMENTS[assignment_id]["canvas_id"])
    except: return "Assignment not found!", 404

    # subject to change
    canvas_assignment_id, unlock_date, initial_due_date, revision_due_date = assignment
    
    if not datetime.date.today() >= datetime.datetime.strptime(unlock_date, "%Y-%m-%d").date():
        return "assignment not unlocked yet", 400

    submission = db.getSubmission(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])
    
    if submission is None:
        submission = db.addSubmission(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])

    # subject to change
    _, _, test_commit, job_id, initial_date, revision_date, initial_commit, revision_commit = submission
    test_comment = None
    initial_comment = None
    revision_comment = None
    job_position = None

    if job_id:
        try:
            job = Job.fetch(job_id, connection=conn)
        except: job = None
        if job:
            if job.is_finished: job_id = None
            else: 
                jobs = q.get_jobs()
                if not job in jobs:
                    job_id = None
                else:
                    try:
                        job_position = jobs.index(job)
                    except ValueError: job_position = 0    
        else: job_id = None

    user_dir = "%s/%s" % (REPOS_DIR, login)
    tests_dir = "%s/%s/student-tests" % (REPOS_DIR, login)
    repo_dir = "%s/%s/submission" % (REPOS_DIR, login)

    if os.path.isdir(repo_dir):
        try:
            repo = git.Repo(repo_dir, search_parent_directories=True)
        except: pass
        else:
            if test_commit:
                try: test_comment = repo.commit(test_commit).message.strip()
                except: test_comment = None
            if initial_commit:
                try: initial_comment = repo.commit(initial_commit).message.strip()
                except: initial_comment = None
            if revision_commit:
                try: revision_comment = repo.commit(revision_commit).message.strip()
                except: revision_comment = None

    return jsonify({
        'job_id': job_id,
        'job_position': job_position,
        'file_exists': os.path.exists(f'{tests_dir}/{assignment_id}.html'),
        'test_commit': test_commit,
        'test_comment': test_comment,
        'initial_due_date': initial_due_date,
        'initial_date': initial_date,
        'initial_commit': initial_commit,
        'initial_comment': initial_comment,
        'revision_due_date': revision_due_date,
        'revision_date': revision_date,
        'revision_commit': revision_commit,
        'revision_comment': revision_comment,
    })

@app.route('/assignments/<assignment_id>/<login>/test_exists')
def test_exists(assignment_id, login):
    tests_dir = "%s/%s/student-tests" % (REPOS_DIR, login)
    return jsonify(os.path.exists("%s/%s.html" % (tests_dir, assignment_id)))

@app.route('/assignments/<assignment_id>/<login>/delete_test', methods=['DELETE'])
def delete_test(assignment_id, login):
    tests_dir = "%s/%s/student-tests" % (REPOS_DIR, login)
    if os.path.exists("%s/%s.html" % (tests_dir, assignment_id)):
        os.remove("%s/%s.html" % (tests_dir, assignment_id))
        return jsonify(True)
    return jsonify(False)

@app.route('/assignments/<assignment_id>/<login>/download_test')
def download_test(assignment_id, login):
    tests_dir = "%s/%s/student-tests" % (REPOS_DIR, login)
    if os.path.exists("%s/%s.html" % (tests_dir, assignment_id)):
        return send_from_directory(tests_dir, "%s.html" % assignment_id)
    return "no file present", 404

def _clone_repo_reset(login):
    ''' Not as dangerous as it looks, but still pretty dangerous. '''
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
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
    #return "Server down for maintainence.", 500
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
    tests_dir = "%s/student-tests" % user_dir
    results_dir = "%s/tool-results" % user_dir
    
    if not os.path.isdir(user_dir):
        os.mkdir(user_dir)
        os.mkdir(tests_dir)
        os.mkdir(results_dir)

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

def _get_last_commit(assignment_id, login, retry=True):
    update_repo(login)
    
    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
    assignment_dir = "%s/%s" % (repo_dir, assignment_id)
    
    try:
        repo = git.Repo(repo_dir, search_parent_directories=True)
        head_commit = str(repo.head.commit)
    except:
        return {'commit_id': None,
                'commit_comment': None,
                'head_commit': None}
    
    if not os.path.isdir(assignment_dir):
        return {'commit_id': None,
                'commit_comment': None,
                'head_commit': head_commit}
    try:
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
        
        return _get_last_commit(assignment_id, login, retry=False)
    
    commit_id = str(commit)
    commit_comment = commit.message.strip()
    return {'commit_id': commit_id,
            'commit_comment': commit_comment,
            'head_commit': head_commit}

@app.route('/assignments/<assignment_id>/<login>/get_last_commit')
def get_last_commit(assignment_id, login):
    return jsonify(_get_last_commit(assignment_id, login))

@app.route('/assignments/<assignment_id>/<login>/test')
def test_assignment(assignment_id, login):
    # return "Server down for maintainence.", 500
    previous_failed = False

    student_id = db.getStudentID(login.lower())

    db.addSubmission(student_id, ASSIGNMENTS[assignment_id]["canvas_id"]) # just in case
    job_id = db.getJob(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])
    if job_id:
        try: job = Job.fetch(job_id, connection=conn)
        except: job = None
        if job:
            if job.is_failed:
                previous_failed = True
            elif not job.is_finished:
                return "Test already running.", 300

    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
    tests_dir = "%s/student-tests" % user_dir
    assignment_name = ASSIGNMENTS[assignment_id]["folder_name"]

    _commit = _get_last_commit(assignment_id, login)
    commit = _commit['commit_id']
    commit_comment = _commit['commit_comment']
    head_commit = _commit['head_commit']
    last_commit = db.getCommit(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])
    
    if not head_commit:
        return f"You haven't made any commits to your repository.", 404
    if not commit:
        return f"No files found in the {assignment_id} folder in your repository.", 404
    
    if not previous_failed and str(last_commit) == str(head_commit):
        return "You haven't pushed any commits since your last test.", 300
    elif not previous_failed and str(last_commit) == str(commit):
        return f"None of your commits since your last test have affected {assignment_name}.", 300
    db.setCommit(student_id, ASSIGNMENTS[assignment_id]["canvas_id"], commit)

    github_link = f'https://github.iu.edu/csci-b351-sp19/{login}-submission/tree/{commit}/{assignment_name}'
    job = q.enqueue_call(
        func=runTest, args=(assignment_id, f'{repo_dir}/{assignment_name}/' if assignment_name != "a2" else f'{repo_dir}/{assignment_name}/code', f'{tests_dir}/{assignment_name}.html', github_link, GRADING_TOOLS_DIR), result_ttl=86400, timeout=600
    )
    if job:
        job_id = job.get_id()
        if not job.is_finished: job_position = q.count
        else: job_position = None
    else:
        return 'Error starting test.', 500

    db.setJob(student_id, ASSIGNMENTS[assignment_id]["canvas_id"], job_id)

    return jsonify({
        'file_exists': False,
        'job_id': job_id,
        'job_position': job_position,
        'test_commit': commit,
        'test_comment': commit_comment
    }), 200

@app.route('/assignments/<assignment_id>/<login>/submit_initial')
def submit_initial(assignment_id, login):
    #return "Server down for maintainence.", 500
    # check we're not too late
    assignment = db.getAssignment(ASSIGNMENTS[assignment_id]["canvas_id"])
    canvas_assignment_id, unlock_date, initial_due_date, revision_due_date = assignment
    basically_today = (datetime.datetime.now() - datetime.timedelta(minutes=30)).date()
    if basically_today > datetime.datetime.strptime(initial_due_date, "%Y-%m-%d").date():
        return "Submission date past.", 400
    
    student_id = db.getStudentID(login.lower())
    student_group = db.getStudent(student_id)[2]
    if student_group == db.TOOL_BASED:
        include_subjective = False
    else:
        include_subjective = True

    db.addSubmission(student_id, ASSIGNMENTS[assignment_id]["canvas_id"]) # just in case

    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
    results_dir = "%s/tool-results" % user_dir
    assignment_name = ASSIGNMENTS[assignment_id]["folder_name"]

    _commit = _get_last_commit(assignment_id, login)
    commit = _commit['commit_id']
    commit_comment = _commit['commit_comment']
    head_commit = _commit['head_commit']
    last_commit = db.getInitialCommit(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])
    
    if not head_commit:
        return f"You haven't made any commits to your repository.", 404
    if not commit:
        return f"No files found in the {assignment_id} folder in your repository.", 404
    
    if str(last_commit) == str(head_commit):
        return "You haven't pushed any commits since your last submission.", 300
    elif str(last_commit) == str(commit):
        return f"None of your commits since your last submission have affected {assignment_name}.", 300

    # Don't run the test if this commit has already been tested!
    now = datetime.date.today()
    db.submitInitial(student_id, ASSIGNMENTS[assignment_id]["canvas_id"], commit, now)

    github_link = f'https://github.iu.edu/csci-b351-sp19/{login}-submission/tree/{commit}/{assignment_name}'
    job = q.enqueue_call(
        func=runGrade, args=(assignment_id, f'{repo_dir}/{assignment_name}/' if assignment_name != "a2" else f'{repo_dir}/{assignment_name}/code', f'{results_dir}/{assignment_name}-initial.html',
            include_subjective, github_link, GRADING_TOOLS_DIR), result_ttl=86400, timeout=600
    )
    if job:
        job_id = job.get_id()
    else:
        return 'Error starting grading tool process.', 500

    return jsonify({
        'initial_date': now,
        'initial_commit': commit,
        'initial_comment': commit_comment
    }), 200

@app.route('/assignments/<assignment_id>/<login>/submit_revision')
def submit_revision(assignment_id, login):
    #return "Server down for maintainence.", 500
    # check we're not too late
    assignment = db.getAssignment(ASSIGNMENTS[assignment_id]["canvas_id"])
    canvas_assignment_id, unlock_date, initial_due_date, revision_due_date = assignment
    if datetime.date.today() <= datetime.datetime.strptime(initial_due_date, "%Y-%m-%d").date():
        return "Initial submission not yet closed.", 400
    basically_today = (datetime.datetime.now() - datetime.timedelta(minutes=30)).date()
    if basically_today > datetime.datetime.strptime(revision_due_date, "%Y-%m-%d").date():
        return "Revision submission deadline past.", 400

    student_id = db.getStudentID(login.lower())
    student_group = db.getStudent(student_id)[2]
    if student_group == db.TOOL_BASED:
        include_subjective = False
    else:
        include_subjective = True

    db.addSubmission(student_id, ASSIGNMENTS[assignment_id]["canvas_id"]) # just in case

    user_dir = "%s/%s" % (REPOS_DIR, login)
    repo_dir = "%s/submission" % user_dir
    results_dir = "%s/tool-results" % user_dir
    assignment_name = ASSIGNMENTS[assignment_id]["folder_name"]

    _commit = _get_last_commit(assignment_id, login)
    commit = _commit['commit_id']
    commit_comment = _commit['commit_comment']
    head_commit = _commit['head_commit']
    last_commit = db.getRevisionCommit(student_id, ASSIGNMENTS[assignment_id]["canvas_id"])
    
    if not head_commit:
        return f"You haven't made any commits to your repository.", 404
    if not commit:
        return f"No files found in the {assignment_id} folder in your repository.", 404
    
    if str(last_commit) == str(head_commit):
        return "You haven't pushed any commits since your last submission.", 300
    elif str(last_commit) == str(commit):
        return f"None of your commits since your last submission have affected {assignment_name}.", 300

    github_link = f'https://github.iu.edu/csci-b351-sp19/{login}-submission/tree/{commit}/{assignment_name}'
    # Don't run the test if this commit has already been tested!
    now = datetime.date.today()
    db.submitRevision(student_id, ASSIGNMENTS[assignment_id]["canvas_id"], commit, now)

    job = q.enqueue_call(
        func=runGrade, args=(assignment_id, f'{repo_dir}/{assignment_name}/' if assignment_name != "a2" else f'{repo_dir}/{assignment_name}/code', f'{results_dir}/{assignment_name}-revision.html',
            include_subjective, github_link, GRADING_TOOLS_DIR), result_ttl=86400
    )
    if job:
        job_id = job.get_id()
    else:
        return 'Error starting grading tool process.', 500

    return jsonify({
        'revision_date': now,
        'revision_commit': commit,
        'revision_comment': commit_comment
    }), 200

@app.route('/admin/<login>/<assignment_id>/initial-feedback')
def download_initial_feedback(login, assignment_id):
    results_dir = "%s/%s/tool-results" % (REPOS_DIR, login)
    if os.path.exists("%s/%s-initial.html" % (results_dir, assignment_id)):
        return send_from_directory(results_dir, "%s-initial.html" % assignment_id)
    return "no file present", 404

@app.route('/admin/<login>/<assignment_id>/revision-feedback')
def download_revision_feedback(login, assignment_id):
    results_dir = "%s/%s/tool-results" % (REPOS_DIR, login)
    if os.path.exists("%s/%s-revision.html" % (results_dir, assignment_id)):
        return send_from_directory(results_dir, "%s-revision.html" % assignment_id)
    return "no file present", 404
