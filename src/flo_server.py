"""
Authors: Prince Modi, Roopkatha Banerjee, Yogesh Simmhan
Emails: princemodi@iisc.ac.in, roopkathab@iisc.ac.in, simmhan@iisc.ac.in
Copyright 2023 Indian Institute of Science
Licensed under the Apache License, Version 2.0, http://www.apache.org/licenses/LICENSE-2.0
"""

import asyncio
from argparse import ArgumentParser
from os import getpid
from threading import Event
from uuid import uuid4

from flask import Flask, jsonify, request
from waitress import serve

from server.server_file_manager import OpenYaML
from server.server_manager import FlotillaServerManager
from utils.monitor import Monitor

app = Flask("flo_server")


process_id: int = getpid()
session_running = Event()
server_config = OpenYaML("./config/server_config.yaml")

parser = ArgumentParser()
parser.add_argument(
    "--monitor",
    action="store_true",
    default=False,
    help="Monitor CPU/RAM/Disk/Network IO",
)
args = parser.parse_args()
is_monitoring = args.monitor
if is_monitoring:
    monitor = Monitor("0", process_id)


def handle_request(
    session_id,
    session_config,
    restore=False,
    revive=False,
    file=False,
):
    session_running.set()
    if is_monitoring:
        monitor.set_session(session_id)
    print("Starting Session:", session_id)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            asyncio.gather(
                flo_server.run(session_id, session_config, restore, revive, file)
            )
        )
    except asyncio.CancelledError:
        print("Session Cancelled")
    except KeyboardInterrupt:
        print("Received KeyboardInterrupt")
    except Exception as e:
        print(e)
        print("Exception in Gather loop")
    finally:
        session_running.clear()
        if is_monitoring:
            monitor.reset_session()
        return session_id


@app.route("/execute_command", methods=["POST"])
def execute_command():
    print("\n[FLOW] flo_server.py: Received request at /execute_command")
    data = request.get_json()
    if session_running.is_set():
        print("[FLOW] flo_server.py: Session Already Running")
        return jsonify({"message": "A session is already running"}), 400
    # Removed check for active clients to allow dynamic joining
    # elif len(flo_server.get_active_clients()) == 0:
    #     print("[FLOW] flo_server.py: No active clients")
    #     return jsonify({"message": "No active clients"}), 400
    elif data and "federated_learning_config" in data:
        print("[FLOW] flo_server.py: Processing federated_learning_config")
        session_config = data["federated_learning_config"]

        if (data["file"] or data["restore"] or data["revive"]) and data["session_id"]:
            restore_session_id = data["session_id"]
            print(f"[FLOW] flo_server.py: Restoring/Reviving session {restore_session_id}")
            session_id = handle_request(
                session_id=restore_session_id,
                session_config=session_config,
                restore=data["restore"],
                revive=data["revive"],
                file=data["file"],
            )
        elif data["session_id"]:
            session_id = data["session_id"]
            print(f"[FLOW] flo_server.py: Starting new session {session_id}")
            handle_request(session_id=session_id,session_config=session_config)

        print(f"[FLOW] flo_server.py: Session {session_id} finished execution")
        return jsonify({"message": f"Session {session_id} finished"}), 200
    else:
        print("[FLOW] flo_server.py: Received Invalid Request")
        return jsonify({"message": "Invalid request"}), 400


def main():
    print("\n[FLOW] flo_server.py: Starting FLo_Server")
    
    # Display Server IP for user convenience
    import socket
    try:
        # Connect to a public DNS to determine the most likely public IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            server_ip = s.getsockname()[0]
            print(f"\n{'='*60}")
            print(f"SERVER IP ADDRESS: {server_ip}")
            print(f"Clients should connect using: --server-ip {server_ip}")
            print(f"{'='*60}\n")
    except Exception:
        print("\n[WARNING] Could not determine public IP. Using localhost/127.0.0.1")

    global flo_server
    flo_server = FlotillaServerManager(server_config)
    print("[FLOW] flo_server.py: FlotillaServerManager initialized")
    serve(
        app,
        host=server_config["comm_config"]["restful"]["rest_hostname"],
        port=server_config["comm_config"]["restful"]["rest_port"],
    )
    print("[FLOW] flo_server.py: Server stopped")


if __name__ == "__main__":
    main()
