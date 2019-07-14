import os
CONF_FILE = os.path.join(os.path.dirname(__file__), 'confs/server.conf')

import json
def load_config(file_path):
    with open(file_path) as json_data_file:
        data = json.load(json_data_file)
    return data

config = load_config(CONF_FILE)

REPOS_DIR = config["repos_dir"]
INSTRUCTORS = config["instructors"]
SITE_URL = config["site_url"]
DB_FILE = config["database_location"]
SECRET_KEY = config["secret_key"]

from .. import SERVER_URL, SILO_SERVER_URL, canvas
SILO_SERVER_URL += "/battles"
SERVER_URL += "/battles"

from . import database as db