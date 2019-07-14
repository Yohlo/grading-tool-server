from flask import Flask
from flask_cors import CORS
from api.grading_tool.silo_server import app as grading_tool
from api.battles.silo_server import app as battles

from api import PORT

app = Flask(__name__)
CORS(app, resources=r'/*', allow_headers='Content-Type')

app.register_blueprint(grading_tool, url_prefix="/grading-tool")
app.register_blueprint(battles, url_prefix="/battles")
app.secret_key = 'keep this secret ;)'
app.run(host='0.0.0.0', port=PORT, debug=True)