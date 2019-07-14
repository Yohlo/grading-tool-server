# /auth
-----

This section of the server handles the OAuth process for GitHub. 
Documentation for this can be found [here](https://developer.github.com/apps/building-oauth-apps/authorizing-oauth-apps/).

----
## Usage

##### /login?app=[app_name]

##### /verify/<app_name>?code=[access_code]

----

Configuration file is of the following format:

```javascript
{
    "github": {
        "client_id": "",
        "client_secret": ""
    },
    "site_urls": {
        "grading_tool": {
            "SUCCESS": "https://url.com/grading-tool/#/OAuth/Success",
            "ERROR": "https://url.com/grading-tool/#/OAuth/Error"
        },
        "battles": {
            "SUCCESS": "https://url.com/battles/#/OAuth/Success",
            "ERROR": "https://url.com/battles/#/OAuth/Error"
        }
    }
}
```