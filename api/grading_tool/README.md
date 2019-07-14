# /grading-tool
-----

This section of the server handles the Grading Tool logic.

----
## Usage

##### todo: fill out usage

----

Configuration file is of the following format:

```javascript
{
    "instructors": [
        {"login_id": "kjyohler", "name": "Kyle Yohler", "id": 5947948},
        {"login_id": "abrleite", "name": "Abe Leite", "id": 6014318}
    ],
    "assignments": {
        "a1": {
            "canvas_id": 9046890,
            "folder_name": "a1"
        },
        "a2": {
            "canvas_id": 9046896,
            "folder_name": "a2"
        }
    },
    "site_url": "https://url.com/grading-tool/#",
    "repos_dir": "",
    "grading_tools_dir": "",
    "database_location": ""
}
```