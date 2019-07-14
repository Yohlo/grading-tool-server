#!/u/b351/python/grading-tool/bin/python
from flask import Flask
from flask_cors import CORS
from wsgiref.handlers import CGIHandler
from api.grading_tool.cgi_server import app as grading_tool
from api.battles.cgi_server import app as battles
from api.auth.cgi_server import app as auth

app = Flask(__name__)
CORS(app, resources=r'/*', allow_headers='Content-Type')

app.register_blueprint(grading_tool, url_prefix="/grading-tool")
app.register_blueprint(battles, url_prefix="/battles")
app.register_blueprint(auth, url_prefix="/auth")

CGIHandler().run(app)