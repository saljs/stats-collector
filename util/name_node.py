#!/bin/env python

# Assign name to a node using the server API
import requests
import argparse
import sys

def get_json(resp):
    """Return json from Response, or exits with error."""
    if not resp.ok:
        print(f"Server returned error: {resp.status_code}", file=sys.stderr)
        print(resp.text)
        sys.exit(1)
    return resp.json()

parser = argparse.ArgumentParser()
parser.add_argument("server", help = "Hostname/IP of the stats server.")
parser.add_argument(
    "--port",
    type = int,
    help = "Port to connect on the stats server.",
    default = 5000,
)
parser.add_argument(
    "--node",
    type = int,
    help = "ID number of the node to name",
    default = None,
)
parser.add_argument(
    "--name",
    help = "Name to assign the node.",
    default = None,
)
args = parser.parse_args()

api_root = f"http://{args.server}:{args.port}/nodes"
selected_node = args.node
new_name = args.name

if selected_node is None:
    # Get list of nodes from server and have user select 1
    all_nodes = get_json(requests.get(api_root))
    print("Select a node:")
    for node in all_nodes:
        print(f"  {node['id']} ({node['name']}): {node['last_ip']}")
    selected_node = int(input("Node ID: "))
if new_name is None:
    # Prompt for name
    new_name = input("New name: ")

# Perform name update
updated = get_json(requests.post(
    f"{api_root}/{selected_node}",
    data = { "name": new_name },
))
print(f"Node {updated['id']} is now named {updated['name']}")
