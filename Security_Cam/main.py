import mqtt
import json
from datetime import datetime
import cv2
import pyaudio as pa
import video as vid
import time
# import threading

# Referenced https://www.javatpoint.com/webcam-motion-detector-in-python and https://towardsdatascience.com/image-analysis-for-beginners-creating-a-motion-detector-with-opencv-4ca6faba4b42 for OpenCV intigration 

with open('information.json') as f:
    data = json.load(f)

host = data['host']
port = data['port']
username = data['user']
password = data['pass']

last_payload = "N/A"
last_status = "N/A"

OPENCV_VIDEOCAPTURE_DEBUG = 1

#Number of days(In seconds) to keep physical on memory backups of videos 
days = 604800

movement_counter = 0
max_movement = 0

# Setting up various classes
CHUNK = 4096
FORMAT = pa.paInt24
RATE = 48000
# For recording and muxing audio
video = vid.VideoRecorder(2560,1440,30,"videos/")
audio = vid.AudioRecorder(CHUNK, FORMAT, 2, RATE)
# AWS setup
aws = vid.Uploading(data['aws'], data['aws_sec'], data['aws_bucket'], data['region'])
delete_vid = vid.DeleteBackups('videos', days)
#MQTT Setup
mqtt_client = mqtt.MQTT(username, password, host, port)

# Used to display time for video feed
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
    
# This is what is used to capture motion, It utilizes OpenCV and Pyaudio 
def motion_dectector():
    global movement_counter
    global max_movement
    global video
    global audio
    previous_frame = None
    prep_frame = None
    contour = None
    prev_motion = 0
    # While Loop for motion
    while True:
        # Reads the video input from the webcam
        check, frame = video.mainVideo.read()
        # Sets up frames to compare based on pure black and white
        prep_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        greyFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prep_frame = cv2.GaussianBlur(src = prep_frame, ksize = (21,21), sigmaX=0)
        # If this is the first time running, it sets the previous frame to now
        if (previous_frame is None):
            previous_frame = prep_frame
            continue

        diff_frame = cv2.absdiff(src1=previous_frame, src2=prep_frame)
        previous_frame = prep_frame
        # Sets up threshold frame
        thresh_frame = cv2.threshold(diff_frame, 25, 255, cv2.THRESH_BINARY)[1]

        thresh_frame = cv2.dilate(thresh_frame, None, 1)

        contours,_ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # If the difference is above motion state, then it triggers recording
        for contour in contours:
            # This compare value adjusts the motions sensitivity
            if cv2.contourArea(contour) < 8000:
                continue
            (x, y, w, h) = cv2.boundingRect(contour)
            motion = 1
            # This compare value adjusts the maximum amount of recording time when movement is found
            if max_movement <= 10000:
                movement_counter = 500 #Final will be 500
                max_movement += 1
                print("movement count is: %s" % (str(max_movement)))
            cv2.rectangle(frame, (x,y),(x+w, y+h), (0,255,0), 2)
        # Sets up time display
        font = cv2.FONT_HERSHEY_SIMPLEX

        frame = cv2.putText(frame, get_time(), (50,50), font, 2, (255,255,255),2,cv2.LINE_AA)
        # If the movement counter is at 0, reset all values for next case of motion
        if movement_counter <= 0:
            motion = 0
            movement_counter = 0
            max_movement = 0
        else:
            # Writes the video and audio frames and adjusts the movement time counter
            # print("movement_counter = " + str(movement_counter))
            video.write_frames(frame)
            audio.write_frame(video.audio_path)
            movement_counter -= 1
        # If the prevous motion was not the current motion, either start recording, take a screenshot, or stop recording and ping MQTT broker with changes of state
        if prev_motion != motion:
            if prev_motion == 0:
                video.start_recording()
                # This is for the screenshot
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                check, frame2 = video.mainVideo.read()
                cv2.imwrite(video.image_path, frame2)
                with open(video.image_path, "rb") as f:
                    content = f.read()
                byteArr = bytearray(content)
                # Sends MQTT broker with the message on the provided topic
                mqtt_client.client.publish("motion_image_livingroom", byteArr, 2)
                f.close()
                mqtt_client.client.publish("webcam_motion", motion)
            else:
                # If the video writer doesnt exist, just skip
                if video.writer is None:
                    video.writer = None
                else:
                    # Stop recording audio and video, proceed to mux the video and audio streams together to produce a video
                    video.stop_recording()
                    audio.stop_recording()
                    process_media = vid.Processing(video.path, video.slowed_path, video.audio_path, video.end_path, video.image_path)
                    process_media.video_produce()
                    video.audio_path = None
                    # Upload the video to the AWS S3 service
                    aws.upload_video(video.end_path, video.aws_video)
                    # Provide the video url and state change to the MQTT Broker
                    mqtt_client.client.publish("video_url", aws.s3_url)
                    mqtt_client.client.publish("webcam_motion", motion)
                    
        prev_motion = motion
        # Used to quit the service when windows are open on the device
        key = cv2.waitKey(1)
        if key == ord('m'):
            break




    video.mainVideo.release()

    cv2.destroyAllWindows()
# Runs the service
motion_dectector()
