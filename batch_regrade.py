## File used to regrade assignments. Script is ran manually.

import api.grading_tool.worker as w
import api.grading_tool.database as db
import git

ASSIGNMENT_ID=9046909
REPOS_DIR = "/u/b351/student-repos"
GRADING_TOOLS_DIR = "/u/b351/class-docs/sp19/admin/sp19/Grading Tools"

students = db.getStudents()

for student in students:
    submission=db.getSubmission(student[0], ASSIGNMENT_ID)
    if not submission: continue
    initial_commit = submission[6]
    if not initial_commit: continue

    if student[2] == db.TOOL_BASED:
        include_subjective = False
    else:
        include_subjective = True

    user_dir = "%s/%s" % (REPOS_DIR, student[1])
    repo_dir = "%s/submission" % user_dir
    results_dir = "%s/tool-results" % user_dir
    try:
        repo = git.Repo(repo_dir, search_parent_directories=True)
        repo.git.checkout(initial_commit)
        repo.git.clean('-fxd')
    except:
        continue
    
    github_link = f'https://github.iu.edu/csci-b351-sp19/{student[1]}-submission/tree/{initial_commit}/a4'
    w.runGrade("a4", f'{repo_dir}/a4', f'{results_dir}/a4-initial.html', include_subjective, github_link, GRADING_TOOLS_DIR)

    print(f'student {student[1]} done!')
