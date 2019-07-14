from . import SERVER_URL, config
from flask import Blueprint, request, redirect
from flask_cors import CORS
import requests

app =  Blueprint('auth', __name__)
CORS(app, resources=r'/*', allow_headers='Content-Type')

## GET /login
# Redirects user to GitHub.IU OAuth authorize page for the b351 OAuth App
@app.route('/login')
def login():
    app_name = request.args.get('app')
    if not app_name:
        return "No app name given", 400
    app_config = config[app_name]
    github = app_config['github']
    return redirect("https://github.iu.edu/login/oauth/authorize?client_id=%s&redirect_uri=%s/verify/%s" % (github['client_id'], SERVER_URL, app_name))

## GET /verify
# Verifies the user using the access code. This is the redirect URI for the GitHub
# OAuth process after authorization. Returns user to main site.
@app.route('/verify/<app_name>')
def verify(app_name):
    app_config = config[app_name]
    github = app_config['github']
    try:
        code = request.args.get('code')
        # Exchange code for access token
        # POST http(s)://[hostname]/login/oauth/access_token
        r = requests.post('https://github.iu.edu/login/oauth/access_token', data = {'client_id':github['client_id'], 'client_secret': github['client_secret'], 'code': code})
        response = r.text
        access_token = response.split('&')[0].split('=')[1]
        
        return redirect(app_config['SUCCESS'] + "?access_token=%s" % access_token)
    except:
        return redirect(app_config['ERROR'])