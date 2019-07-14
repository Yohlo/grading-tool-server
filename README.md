# Server used for Indiana University's CSCI-B351 Into to AI Autograder
-----

This server/web API was created in a rushed timeframe before the start of the Spring 2019 semester to be used for CSCI-B351 Intro to AI as an autograder.

The front-end for the autograder was created using React.js and can be found at this repo: Link (todo)

This project is mostly undocumented. A complete rewrite (with documentation!) for the Fall 2019 semester is currently in progress. 

## Structure
-----

This is a simple flask server that takes advantage of the blueprints feature. There are also two seperate server logics for each blueprint.

IU offers an easy way to host secure server via CGI. The CGI script and server files (flask app wrapped by a CGI handler) handle most of the outbound communcations (i.e., it's what the front-end calls). The standard flask server deals with making modifications to the internal database, accessing the internal redis queue, pulling student files from GitHub and running the test suites. 

The main CGI script can be found in `api.cgi` and the regular flask app can be found in `run_silo_server.py`. The RQ worker is found under `run_worker.py`. 

There are three blueprints used:

#### auth
This blueprint handles authenticating with GitHub OAuth. It takes an `app` parameter to be used as a callback. So a request to `server.com/auth?app=grading-tool` would authenticate the user and redirect to the grading tool homepage. 

#### battles
This blueprint was used for a class-wide Connect 4 AI round-robin tournament. The front end for this can be found here: Link (todo)

#### grading-tool
This is the main blueprint, which has all of the logic for the grading tool. Again, not very well documented. 