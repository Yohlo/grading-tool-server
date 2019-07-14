import redis
import sys
import os

listen = ['default']
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:12345')
conn = redis.from_url(redis_url)

def backup(html_file):
    i = 0
    html_root = html_file.replace('.html','')
    while os.path.isfile(f'{html_root}.{i}.html'):
        i += 1
    open(f'{html_root}.{i}.html', 'w').write(open(html_file, 'r').read())

# Run the student test, this is the function that is pushed to the q
def runTest(assignment_id, submission_dir, html_file, github_link, grading_tools_dir):
    sys.path.append(grading_tools_dir)
    import grade

    tool = grade.tools[assignment_id]
    result = grade.safeGrade(submission_dir, html_file, tool.testSuite, tool.title, redact=True, github_link=github_link)
    backup(html_file)
    return result

def runGrade(assignment_id, submission_dir, html_file, include_subjective, github_link, grading_tools_dir):
    sys.path.append(grading_tools_dir)
    import grade

    tool = grade.tools[assignment_id]
    result = grade.safeGrade(submission_dir, html_file, tool.testSuite, tool.title, redact=False,
        include_subjective=include_subjective, github_link=github_link)
    backup(html_file)
    return result