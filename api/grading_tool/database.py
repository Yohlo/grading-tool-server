from . import INSTRUCTORS

from datetime import datetime, date
import sqlite3
import string
import random
import json

"""  gradingtool.db
 ---------------   ---------------    ------------------
| students      | | assignments   |  | submissions      |
|---------------| |---------------|  |------------------|
| PK id         | | PK id         |  | FK student_id    |
| username      | | unlock_date   |  | FK assignment_id |
| student_group | | initial_date  |  | test_commit      |
 ---------------  | revision_date |  | job_id           |
                   ---------------   | initial_date     |
                                     | revision_date    |
                                     | initial_commit   |
                                     | revision_commit  |
                                      ------------------
"""

from . import DB_FILE

TOOL_BASED = 0
TOOL_ASSISSTED = 1
UNKNOWN = 2

def _getConnection():
    """
    This function creates a db connection and returns that and the cursor.
    Returns:
        conn: the connection to the db DB_FILE
        c:    the cursor
    """
    conn = sqlite3.connect(DB_FILE) # connect to our db
    c = conn.cursor()
    return conn, c

def _initDatabase():
    """
    This function initializes the db from scratch. Useful when testing.
    Returns:
        This function does not return anything.
    """
    conn, c = _getConnection()
    with conn:
        c.execute("DROP TABLE IF EXISTS students")
        c.execute("CREATE TABLE students (id integer PRIMARY KEY, username text, student_group integer)")
        c.execute("DROP TABLE IF EXISTS assignments")
        c.execute("CREATE TABLE assignments (id integer PRIMARY KEY, unlock_date DATE, initial_date DATE, revision_date DATE)")
        c.execute("DROP TABLE IF EXISTS submissions")
        c.execute(''' CREATE TABLE submissions
                (student_id integer, assignment_id integer,
                test_commit text, job_id text,
                initial_date date, revision_date date,
                initial_commit text, revision_commit text,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (assignment_id) REFERENCES assignments (id) ) ''')

def _addAssignments():
    assignments = [(9046890, date(2019, 1, 8), date(2019, 1, 15), date(2019, 1, 22)),
                    (9046896, date(2019, 1, 16), date(2019, 1, 29), date(2019, 2, 5)),
                    (9046903, date(2019, 1, 30), date(2019, 2, 12), date(2019, 2, 19)),
                    (9046909, date(2019, 2, 13), date(2019, 2, 26), date(2019, 3, 5)),
                    (9046936, date(2019, 3, 19), date(2019, 3, 26), date(2019, 4, 2))]
    conn, c = _getConnection()
    with conn:
        for a in assignments:
            c.execute("INSERT INTO assignments(id, unlock_date, initial_date, revision_date) VALUES(?, ?, ?, ?)", a)

def getStudents():
    conn, c = _getConnection()
    with conn:
        c.execute("SELECT * FROM students")
        rows = c.fetchall()
    return rows

def getAssignments():
    conn, c = _getConnection()
    with conn:
        c.execute("SELECT * FROM assignments")
        rows = c.fetchall()
    return rows

def getSubmissions():
    conn, c = _getConnection()
    with conn:
        c.execute("SELECT * FROM submissions")
        rows = c.fetchall()
    return rows

def getAssignment(assignment_id):
    conn, c = _getConnection()
    with conn:
        c.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,))
        assignment = c.fetchone()
    return assignment

def _addStudents(students, tool_assissted_students, tool_based_students):
    conn, c = _getConnection()
    with conn:
        for student in students:
            if student['name'] == "Test Student":
                continue
            username = student['login_id']
            #id = canvas.getStudentID(username)
            c.execute("INSERT INTO students(id, username, student_group) VALUES(?, ?, ?)", (student['id'], username, TOOL_ASSISSTED if username in tool_assissted_students else TOOL_BASED if username in tool_based_students else UNKNOWN))

def getStudent(id):
    conn, c = _getConnection()
    with conn:
        c.execute(''' SELECT * FROM students WHERE id=? ''', (id,))
        student = c.fetchone()
    return student

def getStudentID(login):
    conn, c = _getConnection()
    with conn:
        c.execute(''' SELECT id FROM students WHERE username=? ''', (login,))
        id = c.fetchone()[0]
    return id

def getJob(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT job_id FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        try:
            job_id = c.fetchone()[0]
        except Exception:
            return None
    return job_id

def setJob(student_id, assignment_id, job_id):
    conn, c = _getConnection()
    with conn:
        cmd = "UPDATE submissions SET job_id=\"%s\" WHERE student_id=%s AND assignment_id=%s" % (job_id, student_id, assignment_id)
        c.execute(cmd)
    return job_id

def getCommit(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT test_commit FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        commit = c.fetchone()[0]
    return commit

def setCommit(student_id, assignment_id, commit):
    conn, c = _getConnection()
    with conn:
        cmd = "UPDATE submissions SET test_commit=\"%s\" WHERE student_id=%s AND assignment_id=%s" % (commit, student_id, assignment_id)
        c.execute(cmd)
    return commit

def getInitialCommit(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT initial_commit FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        commit = c.fetchone()[0]
    return commit

def getRevisionCommit(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT revision_commit FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        commit = c.fetchone()[0]
    return commit

def submitInitial(student_id, assignment_id, commit, now):
    conn, c = _getConnection()
    with conn:
        cmd = "UPDATE submissions SET initial_commit=\"%s\" WHERE student_id=%s AND assignment_id=%s" % (commit, student_id, assignment_id)
        c.execute(cmd)
        cmd = f"UPDATE submissions SET initial_date={now} WHERE student_id={student_id} AND assignment_id={assignment_id}"
        c.execute(cmd)
    return commit

def submitRevision(student_id, assignment_id, commit, now):
    conn, c = _getConnection()
    with conn:
        cmd = "UPDATE submissions SET revision_commit=\"%s\" WHERE student_id=%s AND assignment_id=%s" % (commit, student_id, assignment_id)
        c.execute(cmd)
        cmd = f"UPDATE submissions SET revision_date={now} WHERE student_id={student_id} AND assignment_id={assignment_id}"
        c.execute(cmd)
    return commit

def getSubmission(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT * FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        submission = c.fetchone()
    return submission

def addSubmission(student_id, assignment_id):
    conn, c = _getConnection()
    with conn:
        cmd = "SELECT * FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
        c.execute(cmd)
        submission = c.fetchone()
        if submission is None:
            c.execute("INSERT INTO submissions(student_id, assignment_id) VALUES(?, ?)", (student_id, assignment_id))
            cmd = "SELECT * FROM submissions WHERE student_id=%s AND assignment_id=%s" % (student_id, assignment_id)
            c.execute(cmd)
            submission = c.fetchone()
    return submission

def _printTable(table): 
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
#    _initDatabase()
#    _addStudents(canvas.getStudents())
#    _addAssignments()
#    _addStudents(INSTRUCTORS)


    _printTable("students")
    _printTable("assignments")
    _printTable("submissions")

def sync_students():
    from . import canvas

    students = canvas.getStudents()
    new_students = []

    with open("/u/b351/cgi-pub/server/api/grading_tool/confs/tool_based", "r") as f:
        tool_based = f.read()
    with open("/u/b351/cgi-pub/server/api/grading_tool/confs/tool_assisted", "r") as f:
        tool_assisted = f.read()

    for student in students:
        s = getStudent(student['id'])
        if not s:
            print("adding %s" % student['login_id'])
            new_students.append(student)
        
    _addStudents(new_students, tool_assisted, tool_based)
    print(new_students)