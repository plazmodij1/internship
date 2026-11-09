from flask import Flask, request
import subprocess
import json
import os
import uuid


app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    payload = request.json

    print(f"--- INCOMING PAYLOAD ---\n{json.dumps(payload, indent=2)}\n------------------------", flush=True)

    # NetBox sends the object model (e.g., 'device', 'ipaddress', 'contact')
    model = payload.get('model', '')

    req_info = payload.get('request', {})
    path = req_info.get('path', '')

    if '/dcim/devices/' in path or '/ipam/ip-address/' in path:
        playbook = 'sync_device.yml'
    elif '/tenancy/contact/' in path or '/tenancy/contact-assignments/' in path:
        playbook = 'sync_contact.yml'
    else:
        print(f"Ignored webhook for model: {model}")
        return "Ignored object type", 200

    unique_id = uuid.uuid4().hex
    payload_file = f'/tmp/payload_{unique_id}.json'
    with open(payload_file, 'w') as f:
        json.dump({"netbox_payload": payload}, f)

    ansible_command = [
        'ansible-playbook', 
        '-i', 'inventory.yml', 
        playbook,
        '--extra-vars', f"@{payload_file}"
    ]
    
    try:
        result = subprocess.run(ansible_command, cwd='/work', capture_output=True, text=True, check=True)
        print(f"Success ({playbook}):\n{result.stdout}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed ({playbook}):\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}",flush=True)
    finally:
        if os.path.exists(payload_file):
            os.remove(payload_file)

    return "OK", 200

if __name__ == '__main__':
    print("Webhook Receiver Started - File-based JSON parsing...", flush=True) 
    app.run(host='0.0.0.0', port=5000)