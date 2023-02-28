import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time
import cv2
import pandas as pnd
import numpy as np
import subprocess
import wave
import sounddevice as sd
import pyaudio as pa
import os
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

staticBack = None

motionList = [None, None]
movement_counter = 0
writer = None
curr_time_mp4 = None
curr_time_wav = None
file_name = None
slowed_name = None
wf = None

CHUNK = 4096
FORMAT = pa.paInt24
RATE = 48000


time = []

audio_frames = []

dFrame = pnd.DataFrame(columns = ["Initial", "Final"])

# cams_test = 500
# for i in range(0, cams_test):
#     mainVideo = cv2.VideoCapture(i)
#     test, frame = mainVideo.read()
#     if test:
#         print("i : "+str(i)+" /// result: "+str(test))

mainVideo = cv2.VideoCapture(0, cv2.CAP_DSHOW)
mainVideo.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
mainVideo.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
mainVideo.set(cv2.CAP_PROP_FPS, 30)

p = pa.PyAudio()

mainAudio = p.open(
    format=FORMAT,
    channels= 2,
    rate = RATE,
    input = True,
    frames_per_buffer= CHUNK
)

def on_connect(client, data, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("Webcam_living_room")
    client.publish("/online/webcam", "Online", True)
def on_publish(client, user, mid):
    print("Publish was accepted from broker")
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
    global curr_time_mp4
    global curr_time_wav
    global file_name
    global slowed_name
    if datetime.now().hour < 10:
        hour = str(0) + str(datetime.now().hour)
    else:
        hour = str(datetime.now().hour)
    if datetime.now().minute < 10:
        minute = str(0) + str(datetime.now().minute)
    else:
        minute = str(datetime.now().minute)
    if datetime.now().month < 10:
        month = str(0) + str(datetime.now().month)
    else:
        month = str(datetime.now().month)
    if datetime.now().day < 10:
        day = str(0) + str(datetime.now().day)
    else:
        day = str(datetime.now().day)
    curr_time_mp4 = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-v" + ".mp4"
    slowed_name = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-s" + ".mp4"
    file_name = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + ".mp4"
    curr_time_wav = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + ".wav"

def start_recording():
    global writer
    global curr_time_mp4
    get_time()
    print("Writing file with the current time of: " + curr_time_mp4)
    writer = cv2.VideoWriter(curr_time_mp4, cv2.VideoWriter_fourcc(*'MP4V'), 30, (2560,1440))

def end_recording():
    global writer
    global curr_time_wav
    global curr_time_mp4
    global slowed_name
    global file_name
    global audio_frames
    global wf
    if writer is None or audio_frames is None:
        return
    writer.release()
    wf.close()
    audio_frames = []
    cmd = "ffmpeg -i "+ curr_time_mp4 + " -filter:v \"setpts=2.5*PTS\" " + slowed_name
    subprocess.call(cmd, shell=True)
    cmd = "ffmpeg -y -i " + curr_time_wav + " -r 30 -i " + slowed_name + " -filter:a aresample=async=1 -c:a flac -strict -2 -c:v copy " + file_name
    subprocess.call(cmd, shell=True)                                     # "Muxing Done
    print('Muxing Done, cleaning up files')
    

def motion_dectector():
    global motionList
    frame_count = 0
    global movement_counter
    previous_frame = None
    prep_frame = None
    contour = None
    prev_motion = 0
    global writer
    global audio_frames
    global curr_time_wav
    global curr_time_mp4
    global slowed_name
    global file_name
    global wf
    while True:
        frame_count += 1
        check, frame = mainVideo.read()

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
            movement_counter = 300
            cv2.rectangle(frame, (x,y),(x+w, y+h), (0,255,0), 2)


        if movement_counter <= 0:
            motion = 0
            movement_counter = 0
        else:
            print("movement_counter = " + str(movement_counter))
            if writer is None and curr_time_wav is None:
                writer = None
                curr_time_wav = None
            else:
                writer.write(frame)
                data = mainAudio.read(CHUNK)
                audio_frames.append(data)
                wf = wave.open(curr_time_wav, 'wb')
                wf.setnchannels(2)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(audio_frames))
            movement_counter -= 1
        if prev_motion != motion:
            if prev_motion == 0:
                start_recording()
            else:
                if writer is None:
                    print("No writer!")
                    writer = None
                else:
                    print("I was ran")
                    end_recording()
                    os.remove(curr_time_mp4)
                    os.remove(curr_time_wav)
                    os.remove(slowed_name)
                    curr_time_wav = None
            client.publish("motion_livingroom", motion)
        prev_motion = motion
        cv2.imshow("This image captured in Gray Frame", greyFrame)

        cv2.imshow("Difference between the two frames", diff_frame)

        cv2.imshow("This is the threshold frame created from the system's webcam", thresh_frame)

        cv2.imshow("This is the one example of the color frame from the system's webcam", frame)

        key = cv2.waitKey(1)
        if key == ord('m'):
            break




    mainVideo.release()

    cv2.destroyAllWindows()

motion_dectector()
