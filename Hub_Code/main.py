import paho.mqtt.client as mqtt
import requests
import json
import datetime

# Import information.json to use for variables set by user
with open('information.json') as f:
    data = json.load(f)



host = data['host']
port = data['port']

last_payload = "N/A"
last_status = "N/A"

username = data['user']
password = data['pass']

webhookURL = data['weburl']

json_template = {
    "embeds" : [{
        "title" : "Bedroom door status",
        "description" : "**N/A**",
        "timestamp" : "N/A"
    }]
}

subscribe_topics = data['topics']

def bedroom_door_topic(msg):
    global last_payload
    global json_template
    if(str(msg.payload) == last_payload):
        return
    # This is to check if the MQTT data shows the roomdoor as closed
    if(str(msg.payload) == "b'Closed'"):
        # Set timestamp
        utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "Bedroom door status",
        "description" : "**Closed**",
        "timestamp" : utc
    }]
    else:
        utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        json_template["embeds"] = [{
        "title" : "Bedroom door status",
        "description" : "**Open**",
        "timestamp" : utc
    }]
    # Sets the current payload to past to compare to for next on_message callback.
    last_payload = str(msg.payload)

def motion_topic(msg):
    global last_payload
    global json_template
    if(str(msg.payload) == last_payload):
        return
    if(str(msg.payload) == "b'1")

def client_status(msg):
    global last_status
    global json_template
    if(str(msg.payload) == last_status):
        return
    if(str(msg.payload) == "b'offline'"):
        utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "ESP8266 Status Announcement",
        "description" : "BEDROOM DOOR SENSOR IS **OFFLINE**",
        "timestamp" : utc
        }]
    else:
        utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "ESP8266 Status Announcement",
        "description" : "BEDROOM DOOR SENSOR IS **ONLINE**",
        "timestamp" : utc
        }]
    last_status = str(msg.payload)

# When pihub connects to MQTT, send discord webhook to notify connection status
def on_connect(client, userdata,flags,rc):
    print("Connected with result code " + str(rc))
    utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    json_template["embeds"] = [{
        "title" : "MQTT Service Announcement",
        "description" : "MQTT is **online**, with result " + str(rc) + ". Subscribing to topics: " + str(subscribe_topics),
        "timestamp" : utc
    }]
    
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})
    client.subscribe(subscribe_topics)

# When MQTT broker accepts subscription of topics, respond with a print to console of QoS given by the broker
# Added discord webhook notification to know if topics were accepted
def on_subscribe(client, user, mid, msg):
    print("Subscribe accepted from broker with QoS: " + str(msg))
    utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    json_template["embeds"] = [{
        "title" : "MQTT Service Announcement",
        "description" : "MQTT has accepted subscribe with QoS " + str(msg),
        "timestamp" : utc
    }]
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})

def on_message(client, user, msg):
    print("Recieved Message: " + str(msg.payload) + " on topic: " + msg.topic + " with QoS: " + str(msg.qos) + ".")
    # Running into issue where internet catch up caused a repeat of last message
    # This is to compare last message with current to stop this repeated behavior 
    if(str(msg.topic) == "/online/bedroom"):
        client_status(msg)
    elif(str(msg.topic) == "bedroom-door-status"):
        bedroom_door_topic(msg)
    else:
        return
    # webhook post for discord notifications
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})

# If unexpected disconnection to MQTT broker, notify via discord webhook
def on_disconnect(client, user, rc):
    if rc != 0:
        utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        json_template["embeds"] = [{
        "title" : "MQTT Service Announcement",
        "description" : "**Unexpected disconnection from MQTT**",
        "timestamp" : utc
        }]
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})

# Create client
client = mqtt.Client()
# Set callback functions
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message
client.on_disconnect = on_disconnect
# Set username and password given via information.json
client.username_pw_set(username, password)

# Connect to MQTT broker
client.connect(host, port, 60)

client.loop_forever()