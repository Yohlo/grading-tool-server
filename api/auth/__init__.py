import os
CONF_FILE = os.path.join(os.path.dirname(__file__), 'confs/server.conf')

from ..utils import load_config

config = load_config(CONF_FILE)

from .. import SERVER_URL
SERVER_URL += "/auth"