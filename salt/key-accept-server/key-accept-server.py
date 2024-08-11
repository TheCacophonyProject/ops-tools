import yaml
from flask import Flask, request, jsonify
import subprocess
import re

app = Flask(__name__)

# Load configuration
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)

API_PASSWORD = config['password']
PORT = config['port']

def check_key_status(minion_id):
    result = subprocess.run(['sudo', 'salt-key', '--list=all', '--out=json'], capture_output=True, text=True)
    if result.returncode == 0:
        keys = eval(result.stdout)
        if minion_id in keys['minions']:
            return "accepted"
        elif minion_id in keys['minions_pre']:
            return "unaccepted"
        else:
            return "not_found"
    return "error"

def accept_key(minion_id):
    result = subprocess.run(['sudo', 'salt-key', '--accept', minion_id, '-y'], capture_output=True, text=True)
    return result.returncode == 0

@app.route('/accept_key', methods=['POST'])
def accept_salt_key():
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
    password = data.get('password')
    minion_id = data.get('minion_id')

    if password != API_PASSWORD:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if not minion_id:
        return jsonify({"status": "error", "message": "Minion ID is required"}), 400

    if not re.match(r'^tc2-\d{4}$', minion_id):
        return jsonify({"status": "error", "message": "Minion ID must be in the format tc2-1234"}), 400

    key_status = check_key_status(minion_id)

    if key_status == "accepted":
        return jsonify({"status": "success", "message": f"Key for minion {minion_id} is already accepted"})
    elif key_status == "unaccepted":
        if accept_key(minion_id):
            return jsonify({"status": "success", "message": f"Key for minion {minion_id} accepted"})
        else:
            return jsonify({"status": "error", "message": "Failed to accept key"}), 500
    elif key_status == "not_found":
        return jsonify({"status": "error", "message": "Minion ID not found"}), 404
    else:
        return jsonify({"status": "error", "message": "Failed to check key status"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
