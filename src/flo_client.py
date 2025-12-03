"""
Authors: Prince Modi, Roopkatha Banerjee, Yogesh Simmhan
Emails: princemodi@iisc.ac.in, roopkathab@iisc.ac.in, simmhan@iisc.ac.in
Copyright 2023 Indian Institute of Science
Licensed under the Apache License, Version 2.0, http://www.apache.org/licenses/LICENSE-2.0
"""

import argparse
import os
import uuid

from client.client_file_manager import OpenYaML
from client.client_manager import ClientManager
from client.utils.client_info import generate_client_info
from client.utils.monitor import Monitor


def main():
    print("\n[FLOW] flo_client.py: Starting Client")
    pid = os.getpid()
    
    # 1. Parse Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--monitor",
        action="store_true",
        default=False,
        help="Monitor CPU/RAM/Disk/Network usage.",
    )
    parser.add_argument(
        "--client-num",
        type=int,
        default=1,
        help="Client number for running multiple clients (default: 1). Creates separate temp directories and unique ports.",
    )
    parser.add_argument(
        "--server-ip",
        type=str,
        default="localhost",
        help="IP address of the Flotilla Server (MQTT Broker). Default: localhost",
    )
    args = parser.parse_args()
    client_num = args.client_num
    print(f"[FLOW] flo_client.py: Client number: {client_num}")

    # Display Client IP
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            client_ip = s.getsockname()[0]
            print(f"\n{'='*60}")
            print(f"CLIENT IP ADDRESS: {client_ip}")
            print(f"{'='*60}\n")
    except Exception:
        print("\n[WARNING] Could not determine Client IP.")

    # 2. Load and Modify Configuration
    client_config = OpenYaML(os.path.join("config", "client_config.yaml"))
    
    # A. Modify Temp Directory
    base_temp_dir = client_config["general_config"]["temp_dir_path"]
    temp_dir_path = os.path.join(f"{base_temp_dir}_{client_num}")
    client_config["general_config"]["temp_dir_path"] = temp_dir_path
    print(f"[FLOW] flo_client.py: Using temp directory: {temp_dir_path}")
    
    # B. Modify MQTT Client Name
    original_client_name = client_config["comm_config"]["mqtt"]["client_name"]
    client_config["comm_config"]["mqtt"]["client_name"] = f"{original_client_name}_{client_num}"
    print(f"[FLOW] flo_client.py: MQTT client name: {client_config['comm_config']['mqtt']['client_name']}")
    
    # C. Modify gRPC Ports (Offset by (client_num - 1) * 2)
    # Client 1: 50053, 50054
    # Client 2: 50055, 50056
    port_offset = (client_num - 1) * 2
    original_sync_port = client_config["comm_config"]["grpc"]["sync_port"]
    original_async_port = client_config["comm_config"]["grpc"]["async_port"]
    
    client_config["comm_config"]["grpc"]["sync_port"] = original_sync_port + port_offset
    client_config["comm_config"]["grpc"]["async_port"] = original_async_port + port_offset
    
    print(f"[FLOW] flo_client.py: gRPC Sync Port: {client_config['comm_config']['grpc']['sync_port']}")
    print(f"[FLOW] flo_client.py: gRPC Sync Port: {client_config['comm_config']['grpc']['sync_port']}")
    print(f"[FLOW] flo_client.py: gRPC Async Port: {client_config['comm_config']['grpc']['async_port']}")

    # D. Modify MQTT Broker IP
    server_ip = args.server_ip
    if server_ip != "localhost":
        client_config["comm_config"]["mqtt"]["mqtt_broker"] = server_ip
        print(f"[FLOW] flo_client.py: Overriding MQTT Broker IP to: {server_ip}")
    else:
        print(f"[FLOW] flo_client.py: Using default MQTT Broker IP: {client_config['comm_config']['mqtt']['mqtt_broker']}")

    # 3. Load or Generate Client Info
    if os.path.isfile(os.path.join(temp_dir_path, "client_info.yaml")):
        client_info = OpenYaML(os.path.join(temp_dir_path, "client_info.yaml"))
        client_id: str = client_info["client_id"]
        print(f"[FLOW] flo_client.py: Loaded existing client info for ID: {client_id}")
    else:
        client_id: str = str(uuid.uuid4())
        client_info = generate_client_info(client_id, temp_dir_path)
        print(f"[FLOW] flo_client.py: Generated new client info for ID: {client_id}")
    
    print(f"[FLOW] flo_client.py: MQTT Client ID will be: FedML_client_{client_id}")

    # 4. Start Monitor (if requested)
    if args.monitor:
        print("[FLOW] flo_client.py: Starting Monitor")
        Monitor(client_id, pid)

    # 5. Start Client Manager
    print("[FLOW] flo_client.py: Initializing ClientManager")
    client = ClientManager(client_id, client_config, client_info)
    print("[FLOW] flo_client.py: Running ClientManager")
    client.run()


if __name__ == "__main__":
    main()
