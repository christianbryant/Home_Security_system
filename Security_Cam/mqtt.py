import paho.mqtt.client as mqtt
import json

class MQTT:
    def __init__(self, username, password, host, port):
        self.user = username
        self.password = password
        self.host = host
        self.port = port
        # Create client
        self.client = mqtt.Client()
        # Set callback functions
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
        # Set username and password given via information.json
        self.client.username_pw_set(self.user, self.password)
        self.client.will_set("/online/webcam", "Offline", 2, True)
        # Connect to MQTT broker
        self.client.loop_start()
        self.client.connect(self.host, self.port, 60)
    
    def on_connect(self, client, data, flags, rc):
        print("Connected with result code " + str(rc))
        self.client.subscribe("Webcam_living_room")
        self.client.publish("/online/webcam", "Online", True)
    
    def on_publish(self, client, user, mid):
        print("Publish was accepted from broker")

    def on_disconnect(self, client, user, rc):
        if rc != 0:
            print("Unexpected disconnect from MQTT Broker!")
