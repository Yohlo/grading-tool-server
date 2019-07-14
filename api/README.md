# /
-----

This is the main section of the server/api. Mainly serves as a package with global configs for each blueprint and utils. 

----

Configuration file is of the following format:

```javascript
{
    "canvas": {
        "URL": "https://lmsproxy.uits.iu.edu/lmspx-prd/canvas/",
        "token": "",
        "course_id": ""
    },
    "cgi_server_url": "https://url.com/server/api.cgi",
    "silo_server_url": "http://dif-url.com",
    "silo_server_port": 30005
}
```