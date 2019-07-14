import json

def load_config(file_path):
    with open(file_path) as json_data_file:
        data = json.load(json_data_file)
    return data