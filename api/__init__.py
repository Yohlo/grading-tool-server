import os
CONF_FILE = os.path.join(os.path.dirname(__file__), 'confs/server.conf')

from .utils import load_config
config = load_config(CONF_FILE)

SERVER_URL = config["cgi_server_url"]
SILO_SERVER_URL = config["silo_server_url"]
PORT = config["silo_server_port"]
SILO_SERVER_URL = f"{SILO_SERVER_URL}:{PORT}"

from .utils.canvas import Canvas
canvas = Canvas(config["canvas"]["token"], config["canvas"]["course_id"], config["canvas"]["URL"])