import paho.mqtt.client as mqtt
import requests
import json
from datetime import datetime
import boto3 as boto
from boto3.s3.transfer import S3Transfer
import os

# Import information.json to use for variables set by user
with open('information.json') as f:
    data = json.load(f)

credentials = { 
    'aws_access_key_id': data['aws'],
    'aws_secret_access_key': data['aws_sec']
}


def get_time():
    if datetime.now().hour < 10:
        hour = str(0) + str(datetime.now().hour)
    else:
        hour = str(datetime.now().hour)
    if datetime.now().minute < 10:
        minute = str(0) + str(datetime.now().minute)
    else:
        minute = str(datetime.now().minute)
    if datetime.now().second < 10:
        second = str(0) + str(datetime.now().second)
    else:
        second = str(datetime.now().second)
    if datetime.now().month < 10:
        month = str(0) + str(datetime.now().month)
    else:
        month = str(datetime.now().month)
    if datetime.now().day < 10:
        day = str(0) + str(datetime.now().day)
    else:
        day = str(datetime.now().day)
    time_file = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second + ".jpg"
    return time_file

bucket_name = data['aws_bucket']
region = data['region']


def image_upload(filename):
    s3_client = boto.client('s3', region, **credentials)

    s3_transfer = S3Transfer(s3_client)

    curr_time = get_time()

    s3_transfer.upload_file(filename, bucket_name,  curr_time, 
                    extra_args={'ACL': 'public-read', 'ContentType': 'image/jpeg'})


    #https://"bucket_name".s3."region".amazonaws.com/"filename"
    s3_url = str("https://" + bucket_name + ".s3." + region + ".amazonaws.com/" + curr_time)
    return s3_url



host = data['host']
port = data['port']

last_payload = "N/A"
last_status_esp = "N/A"
last_status_cam = "N/A"
img_url = "N/A"
video_url = "N/A"

username = data['user']
password = data['pass']

webhookURL = data['weburl']

json_last = "N/A"
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
    # This is to check if the MQTT data shows the roomdoor as closed
    if(str(msg.payload) == "b'Closed'"):
        # Set timestamp
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "Bedroom door status",
        "description" : "**Closed**",
        "timestamp" : utc
    }]
    else:
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        json_template["embeds"] = [{
        "title" : "Bedroom door status",
        "description" : "**Open**",
        "timestamp" : utc
    }]
    # Sets the current payload to past to compare to for next on_message callback.

def motion_topic(msg):
    global last_payload
    global json_template
    global img_url
    global video_url
    if((str(msg.payload) == "b'1'")&(img_url != "N/A")):
        print("Ive been ran with the payload: %s and %s is the image" %(str(msg.payload), img_url))
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "Security Camera Status Announcement",
        "description" : "Living room motion **DETECTED**",
        "timestamp" : utc,
        "image" : {
            "url": img_url
        }
        }]
    elif((str(msg.payload) == "b'0'")):
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        json_temp = {
            "embeds" : [{
                "title" : "Security Camera Status Announcement",
                "description" : "Living room motion **STOPPED**",
                "timestamp" : utc
                }
            ]}
        json_video = {
        "content" : video_url,
        }
        req = requests.post(webhookURL, data = json.dumps(json_temp), headers = {'Content-type' : 'application/json'})
        req = requests.post(webhookURL, data = json.dumps(json_video), headers = {'Content-type' : 'application/json'})
    else:
        return
    
    
        
def motion_video(msg):
    global last_payload
    global video_url
    video_url = str(msg.payload)
    video_url = video_url.replace("b'", "")
    video_url = video_url.replace("'", "")

def motion_image(msg):
    global img_url
    global last_payload
    f = open('temp.jpg', "wb")
    f.write(msg.payload)
    f.close()
    img_url = image_upload('temp.jpg')
    os.remove('temp.jpg')

def client_status(msg):
    global last_status_esp
    global json_template
    if(str(msg.payload) == last_status_esp):
        return
    if(str(msg.payload) == "b'offline'"):
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "ESP8266 Status Announcement",
        "description" : "BEDROOM DOOR SENSOR IS **OFFLINE**",
        "timestamp" : utc
        }]
    else:
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "ESP8266 Status Announcement",
        "description" : "BEDROOM DOOR SENSOR IS **ONLINE**",
        "timestamp" : utc
        }]
    last_status_esp = str(msg.payload)

def client_status_camera(msg):
    global last_status_cam
    global json_template
    if(str(msg.payload) == last_status_cam):
        return
    if(str(msg.payload) == "b'Offline'"):
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "Security Camera Status Announcement",
        "description" : "LIVING ROOM CAMERA IS **OFFLINE**",
        "timestamp" : utc
        }]
    else:
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        # Update template to post to discord webhook integration with updated door status
        json_template["embeds"] = [{
        "title" : "Security Camera Status Announcement",
        "description" : "LIVING ROOM CAMERA IS **ONLINE**",
        "timestamp" : utc
        }]
    last_status_cam = str(msg.payload)

# When pihub connects to MQTT, send discord webhook to notify connection status
def on_connect(client, userdata,flags,rc):
    print("Connected with result code " + str(rc))
    utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
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
    utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    json_template["embeds"] = [{
        "title" : "MQTT Service Announcement",
        "description" : "MQTT has accepted subscribe with QoS " + str(msg),
        "timestamp" : utc
    }]
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})

def on_message(client, user, msg):
    global json_last
    global json_template
    if (str(msg.topic) != "motion_image_livingroom"):
        print("Recieved Message: " + str(msg.payload) + " on topic: " + msg.topic + " with QoS: " + str(msg.qos) + ".")
    else:
        print("Recieved an image!")
    # Running into issue where internet catch up caused a repeat of last message
    # This is to compare last message with current to stop this repeated behavior 
    if(str(msg.topic) == "/online/bedroom"):
        client_status(msg)
    elif (str(msg.topic) == "/online/webcam"):
        client_status_camera(msg)
    elif(str(msg.topic) == "bedroom-door-status"):
        bedroom_door_topic(msg)
    elif(str(msg.topic) == "motion_image_livingroom"):
        motion_image(msg)
    elif(str(msg.topic) == "webcam_motion"):
        motion_topic(msg)
    elif(str(msg.topic) == "video_url"):
        motion_video(msg)
    else:
        return
    # webhook post for discord notifications
    if(str(json_template["embeds"]) == str(json_last)):
            return
    
    req = requests.post(webhookURL, data = json.dumps(json_template), headers = {'Content-type' : 'application/json'})
    print(json_template["embeds"])
    json_last = str(json_template["embeds"])

# If unexpected disconnection to MQTT broker, notify via discord webhook
def on_disconnect(client, user, rc):
    if rc != 0:
        utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
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