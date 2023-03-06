import paho.mqtt.client as mqtt
import json
from datetime import datetime
import cv2
import pyaudio as pa
import video as vid
# import threading

# Referenced https://www.javatpoint.com/webcam-motion-detector-in-python and https://towardsdatascience.com/image-analysis-for-beginners-creating-a-motion-detector-with-opencv-4ca6faba4b42 for OpenCV intigration 

with open('information.json') as f:
    data = json.load(f)

OPENCV_VIDEOCAPTURE_DEBUG=1
host = data['host']
port = data['port']

last_payload = "N/A"
last_status = "N/A"

username = data['user']
password = data['pass']

#Number of days(In seconds) to keep physical on memory backups of videos 
days = 604800

staticBack = None

movement_counter = 0
wf = None

CHUNK = 4096
FORMAT = pa.paInt24
RATE = 48000
video = vid.VideoRecorder(2560,1440,30,"videos/")
audio = vid.AudioRecorder(CHUNK, FORMAT, 2, RATE)
aws = vid.Uploading(data['aws'], data['aws_sec'], data['aws_bucket'], data['region'])
delete_vid = vid.DeleteBackups('videos', days)

audio_frames = []

# cams_test = 500
# for i in range(0, cams_test):
#     mainVideo = cv2.VideoCapture(i)
#     test, frame = mainVideo.read()
#     if test:
#         print("i : "+str(i)+" /// result: "+str(test))

def on_connect(client, data, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("Webcam_living_room")
    client.publish("/online/webcam", "Online", True)
def on_publish(client, user, mid):
    print("Publish was accepted from broker")
    delete_vid.delete_files()
def on_disconnect(client, user, rc):
    if rc != 0:
        print("Unexpected disconnect from MQTT Broker!")


# Create client
client = mqtt.Client()
# Set callback functions
client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect
# Set username and password given via information.json
client.username_pw_set(username, password)
client.will_set("/online/webcam", "Offline", 2, True)
# Connect to MQTT broker
client.loop_start()
client.connect(host, port, 60)



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
    
    time_display = str(datetime.now().year) + "-" + month + "-" +  day + " " + hour + ":" + minute + ":" + second
    return time_display
    

def motion_dectector():
    global movement_counter
    global video
    global audio
    previous_frame = None
    prep_frame = None
    contour = None
    prev_motion = 0
    while True:
        check, frame = video.mainVideo.read()

        prep_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        greyFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prep_frame = cv2.GaussianBlur(src = prep_frame, ksize = (21,21), sigmaX=0)

        if (previous_frame is None):
            previous_frame = prep_frame
            continue

        diff_frame = cv2.absdiff(src1=previous_frame, src2=prep_frame)
        previous_frame = prep_frame

        thresh_frame = cv2.threshold(diff_frame, 25, 255, cv2.THRESH_BINARY)[1]

        thresh_frame = cv2.dilate(thresh_frame, None, 1)

        contours,_ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) < 1000:
                continue
            (x, y, w, h) = cv2.boundingRect(contour)
            motion = 1
            movement_counter = 1000 #Final will be 1000
            cv2.rectangle(frame, (x,y),(x+w, y+h), (0,255,0), 2)

        font = cv2.FONT_HERSHEY_SIMPLEX

        frame = cv2.putText(frame, get_time(), (50,50), font, 2, (255,255,255),2,cv2.LINE_AA)
        if movement_counter <= 0:
            motion = 0
            movement_counter = 0
        else:
            print("movement_counter = " + str(movement_counter))
            video.write_frames(frame)
            audio.write_frame(video.audio_path)
            movement_counter -= 1
        if prev_motion != motion:
            if prev_motion == 0:
                video.start_recording()
                cv2.imwrite(video.image_path, frame)
                with open(video.image_path, "rb") as f:
                    content = f.read()
                byteArr = bytearray(content)
                client.publish("motion_image_livingroom", byteArr, 2)
                f.close()
            else:
                if video.writer is None:
                    video.writer = None
                else:
                    video.stop_recording()
                    audio.stop_recording()
                    process_media = vid.Processing(video.path, video.slowed_path, video.audio_path, video.end_path, video.image_path)
                    process_media.video_produce()
                    video.audio_path = None
                    aws.upload_video(video.end_path, video.aws_video)
                    client.publish("video_url", aws.s3_url)
                    
            client.publish("webcam_motion", motion)
        prev_motion = motion

        # cv2.imshow("This is the threshold frame created from the system's webcam", thresh_frame)

        # cv2.imshow("This is the one example of the color frame from the system's webcam", frame)

        key = cv2.waitKey(1)
        if key == ord('m'):
            break




    video.mainVideo.release()

    cv2.destroyAllWindows()

motion_dectector()
