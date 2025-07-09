# instalovat jsonschema
# pip install jsonschema
# pip install phenopackets protobuf
# pip install wxpython

import json
from google.protobuf.json_format import Parse, ParseError
from phenopackets import Phenopacket

import os

# Get the directory where the script is located
base_dir = os.path.dirname(os.path.abspath(__file__))
file_name = 'male1.json'
file_path = os.path.join(base_dir, file_name)

# Read the JSON data
with open(file_path, 'r') as f:
    json_data = f.read()


# Try to parse the JSON into a Protobuf Phenopacket message
try:
    phenopacket = Parse(json_data, Phenopacket())
    print("Phenopacket", file_name, "is valid according to the Protobuf schema.")
except ParseError as e:
    print("Validation error:", e)

