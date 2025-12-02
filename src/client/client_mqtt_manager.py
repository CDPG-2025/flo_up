"""
Authors: Prince Modi, Roopkatha Banerjee, Yogesh Simmhan
Emails: princemodi@iisc.ac.in, roopkathab@iisc.ac.in, simmhan@iisc.ac.in
Copyright 2023 Indian Institute of Science
Licensed under the Apache License, Version 2.0, http://www.apache.org/licenses/LICENSE-2.0
"""

import json
import os
import time
from threading import Event

import paho.mqtt.client as mqtt

from client.client_file_manager import get_available_models
from client.utils.ip import get_ip_address, get_ip_address_docker
from utils.hardware_info import get_hardware_info
from utils.logger import FedLogger


class ClientMQTTManager:
    def __init__(
        self,
        id: str,
        mqtt_config: dict,
        grpc_config: dict,
        temp_dir_path: str,
        dataset_details: dict,
        client_info: dict,
    ) -> None:

        # -----------------------------
        # LOAD CONFIG BEFORE USING THEM
        # -----------------------------
        self.client_id: str = id
        self.client_name: str = mqtt_config["client_name"]

        # MQTT config
        self.type_: str = mqtt_config["type"]
        self.mqtt_broker: str = mqtt_config["mqtt_broker"]
        self.mqtt_broker_port: int = int(mqtt_config["mqtt_broker_port"])
        self.mqtt_heartbeat_timeout_s: float = float(mqtt_config["heartbeat_timeout_s"])

        # MQTT topics
        self.mqtt_server_topic: str = mqtt_config["mqtt_server_topic"]
        self.mqtt_client_topic: str = mqtt_config["mqtt_client_topic"]

        # Remove unnecessary overwrites (your original code was overwriting these)
        # self.mqtt_server_topic = "advert_server"
        # self.mqtt_client_topic = "advert_client"

        # gRPC config
        self.grpc_port: str = str(grpc_config["sync_port"])
        self.grpc_workers: int = grpc_config["workers"]

        # Context info
        self.temp_dir_path: str = temp_dir_path
        self.dataset_details: dict = dataset_details
        self.client_info: dict = client_info

        # Logger & hardware info
        self.logger: FedLogger = FedLogger(
            id=self.client_id, loggername="CLIENT_MQTT_MANAGER"
        )
        self.hw_info: dict = get_hardware_info()

        # -----------------------------
        # DETECT DOCKER IP MODE
        # -----------------------------
        try:
            ev = eval(os.environ["DOCKER_RUNNING"])
        except KeyError:
            ev = False

        if ev:
            self.ip: str = get_ip_address_docker()
        else:
            self.ip: str = get_ip_address(self.mqtt_broker, self.mqtt_broker_port)

        self.grpc_ep: str = f"{self.ip}:{self.grpc_port}"

        # Synchronization flag
        self.heard_from_server_event = Event()
        self.session_id = None

    # --------------------------------------------------------
    #                    MQTT SUBSCRIBER
    # --------------------------------------------------------
    def mqtt_sub(self, event_flag):
        print("[FLOW] client_mqtt_manager.py: Starting mqtt_sub")

        def on_connect(client, userdata, flags, rc):
            self.logger.info("MQTT.client.connect", f"MQTT connection status,{rc}")
            print(f"[FLOW] client_mqtt_manager.py: MQTT Connected with result code {rc}")

        def on_subscribe(client, userdata, mid, granted_qos):
            self.logger.info("MQTT.client.subscribe", f"subscribe tracking variable:,{mid}")
            print(f"[FLOW] client_mqtt_manager.py: MQTT Subscribed (mid={mid})")

        def on_publish(client, userdata, mid):
            self.logger.info("MQTT.client.publish", f"publish tracking variable:,{mid}")

        def message_ad_response(client, userdata, message):
            info = json.loads(message.payload.decode())
            print(f"[FLOW] client_mqtt_manager.py: Received ad response from server: {info}")

            # Update from server response
            self.mqtt_heartbeat_timeout_s = info["heartbeat_interval"]
            self.mqtt_client_topic = info["mqtt_client_topic"]

            self.logger.info("MQTT.client.advertise.response", info)

            # Build client advertisement payload
            payload = json.dumps(
                {
                    self.client_id: {
                        "payload": {
                            "type": self.type_,
                            "timestamp": time.time(),
                            "grpc_ep": self.grpc_ep,
                            "cluster_id": 0,
                            "hw_info": self.hw_info,
                            "datasets": self.dataset_details,
                            "models": get_available_models(self.temp_dir_path),
                            "benchmark_info": self.client_info["benchmark_info"],
                            "name": self.client_name,
                        }
                    }
                }
            )

            print(f"[FLOW] client_mqtt_manager.py: Publishing client advertisement to {self.mqtt_client_topic}")
            client.publish(self.mqtt_client_topic, payload)
            userdata.set()

        client_userdata = self.heard_from_server_event
        client = mqtt.Client(f"FedML_client_{self.client_id}", userdata=client_userdata)

        client.on_connect = on_connect
        client.on_subscribe = on_subscribe
        client.on_publish = on_publish

        print(f"[FLOW] client_mqtt_manager.py: Connecting to MQTT broker {self.mqtt_broker}:{self.mqtt_broker_port}")
        client.connect(self.mqtt_broker, self.mqtt_broker_port, keepalive=60)

        client.message_callback_add(self.mqtt_server_topic, message_ad_response)
        client.loop_start()
        client.subscribe(self.mqtt_server_topic)

        print(f"[FLOW] client_mqtt_manager.py: Subscribed to {self.mqtt_server_topic}")
        print("[FLOW] client_mqtt_manager.py: Waiting for server advertisement")

        self.heard_from_server_event.wait()
        print("[FLOW] client_mqtt_manager.py: Server advertisement received")

        # Heartbeat loop
        while not event_flag.is_set():
            payload = json.dumps({"id": self.client_id, "timestamp": time.time()})
            client.publish("heartbeat", payload)
            event_flag.wait(self.mqtt_heartbeat_timeout_s)

        print("[FLOW] client_mqtt_manager.py: Stopping MQTT loop")
        client.loop_stop()

