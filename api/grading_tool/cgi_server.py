from . import SITE_URL, SERVER_URL, SILO_SERVER_URL, REPOS_DIR, INSTRUCTORS, ASSIGNMENTS, SECRET_KEY
from . import database as db
from . import canvas

from flask import Blueprint, jsonify, request, redirect, send_from_directory, send_file, Response
from datetime import date, datetime
from flask_cors import CORS
import requests
import shutil
import json
import git
import os

app =  Blueprint('grading-tool', __name__)
CORS(app, resources=r'/*', allow_headers='Content-Type')

silo_headers = {"secret_key": SECRET_KEY}

def checkJob(job_id):
    if not job_id:
        return False
    r = requests.get("%s/check/%s" % (SILO_SERVER_URL, job_id), headers=silo_headers)
    result = r.json()
    if r.status_code == 200:
        job_is_finished = bool(result)
    else:
        job_is_finished = True # (?)
    return job_is_finished

def is_admin(login):
    for instructor in INSTRUCTORS:
        if instructor["login_id"] == login:
            return True
    return False        

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route('/')
def hello():
    return "Hello, World! You're quite curious :)"

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
    
    # TODO: Move to silo server
    student_id = db.getStudentID(user['login'].lower())
    if not student_id:
        return 'Student not found in our records.', 404
    student_info = db.getStudent(student_id)

    return jsonify({
        'login': user['login'],
        'name': user['name'],
        'avatar_url': user['avatar_url'],
        'student_group': student_info[2],
        'is_admin': is_admin(user['login'])
    })

def _parseStudent(student):
    return {
        'login': student['login_id'],
        'name': student['name']
    }

@app.route('/students')
def students():
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    if not is_admin(user['login'].lower()):
        return "Not authorized", 400

    students = canvas.getStudents()
    students[:] = [s for s in students if s.get('name') != "Test Student"]
    students = list(map(_parseStudent, students))
    students.extend(map(_parseStudent, INSTRUCTORS))

    return jsonify(students)

@app.route('/assignments/<assignment_id>')
def getAssignment(assignment_id):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    a = requests.get(f"{SILO_SERVER_URL}/assignments/{assignment_id}/{user['login']}/info", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

# special one for admins :)
@app.route('/assignments/<assignment_id>/<login>')
def getStudentAssignment(assignment_id, login):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    if not is_admin(user['login'].lower()):
        return "Not authorized", 400

    a = requests.get(f"{SILO_SERVER_URL}/assignments/{assignment_id}/{login}/info", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

@app.route('/assignments')
def getAssignments():

    # TODO: Move to silo
    assignments = db.getAssignments()

    response = []
    i = 1
    for assignment in assignments:
        response.append({
            'id': i,
            'canvas_id': assignment[0],
            'unlocked': date.today() >= datetime.date(datetime.strptime(assignment[1], "%Y-%m-%d")),
            'initial_date': assignment[2],
            'revision_date': assignment[3]
        })
        i += 1

    return jsonify(response)

## GET /test/:assignment_id/start
# starts the tests for the student to the given assignment
@app.route('/test/<assignment_id>/start')
def test_assignment(assignment_id):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    a = requests.get(f"{SILO_SERVER_URL}/assignments/{assignment_id}/{user['login']}/test", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

@app.route("/test/<assignment_id>/check/<job_key>")
def check_job(assignment_id, job_key):
    job_is_finished = checkJob(job_key)

    if job_is_finished:
        return jsonify(True)
    else:
        return jsonify(requests.get("%s/check/%s/position" % (SILO_SERVER_URL, job_key), headers=silo_headers).text), 202

@app.route("/test/<assignment_id>/download")
def download_html_file(assignment_id):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    a = requests.get("%s/assignments/%s/%s/download_test" % (SILO_SERVER_URL, ASSIGNMENTS[assignment_id]["folder_name"], user['login']), headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

# special one for admins :)
@app.route("/test/<assignment_id>/<login>/download")
def download_students_test_html_file(assignment_id, login):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    if not is_admin(user['login'].lower()):
        return "Not authorized", 400

    a = requests.get("%s/assignments/%s/%s/download_test" % (SILO_SERVER_URL, ASSIGNMENTS[assignment_id]["folder_name"], login), headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

# special one for admins :)
@app.route("/initial/<assignment_id>/<login>/download")
def download_students_initial_html_file(assignment_id, login):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    if not is_admin(user['login'].lower()):
        return "Not authorized", 400

    a = requests.get("%s/admin/%s/%s/initial-feedback" % (SILO_SERVER_URL, login, ASSIGNMENTS[assignment_id]["folder_name"]), headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

# special one for admins :)
@app.route("/revision/<assignment_id>/<login>/download")
def download_students_revision_html_file(assignment_id, login):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()

    if not is_admin(user['login'].lower()):
        return "Not authorized", 400

    a = requests.get("%s/admin/%s/%s/revision-feedback" % (SILO_SERVER_URL, login, ASSIGNMENTS[assignment_id]["folder_name"]), headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

@app.route('/submit/<assignment_id>/initial')
def submit_initial(assignment_id):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    a = requests.get(f"{SILO_SERVER_URL}/assignments/{assignment_id}/{user['login']}/submit_initial", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code

@app.route('/submit/<assignment_id>/revision')
def submit_revision(assignment_id):
    code = request.args.get('access_token')
    if not code:
        return "No access code given", 400
    r = requests.get("https://github.iu.edu/api/v3/user?access_token=%s" % code)
    if r.status_code != requests.codes.ok:
        return "Issue retrieving user based on given access code", r.status_code
    user = r.json()
    
    a = requests.get(f"{SILO_SERVER_URL}/assignments/{assignment_id}/{user['login']}/submit_revision", headers=silo_headers)
    if a.status_code == 500:
        return 'Internal server error - email Kyle for support.', 500
    return a.content, a.status_code
