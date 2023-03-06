import cv2
import wave
import pyaudio as pa
import subprocess
import os
from datetime import datetime
import time
import boto3 as boto
from boto3.s3.transfer import S3Transfer

class VideoRecorder:
    def __init__(self, width, height, fps, folder):
        self.width = width
        self.height = height
        self.fps = fps
        self.folder = folder
        self.path = None
        self.audio_path = None
        self.slowed_path = None
        self.end_path = None
        self.image_path = None
        self.writer = None
        self.frame = None
        self.mainVideo = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.mainVideo.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.mainVideo.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.mainVideo.set(cv2.CAP_PROP_FPS, self.fps)

    def get_time(self):
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
        self.path = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second + "-v" + ".mp4"
        self.audio_path = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second +".wav"
        self.slowed_path = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second + "-s" + ".mp4"
        self.end_path = str(self.folder) + str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second +".mp4"
        self.image_path = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second +".jpg"
        self.aws_video = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-" + second +".mp4"

    def start_recording(self):
        self.get_time()
        if self.width != int(self.mainVideo.get(3)) or self.height != int(self.mainVideo.get(4)):
            print("Video definition mismatch! Resolution provided to VideoRecorder is not available on webcam...")
            print("Now using OpenCV defaults: width = " + str(int(self.mainVideo.get(3))) + " and Height = " + str(int(self.mainVideo.get(4))))
            self.width = int(self.mainVideo.get(3))
            self.height = int(self.mainVideo.get(4))
        self.writer = cv2.VideoWriter(self.path, cv2.VideoWriter_fourcc(*'mp4v'), self.fps, (int(self.width),int(self.height)))

    def write_frames(self, frame):
        if self.writer is None:
            return
        self.frame = frame
        cv2.imshow("Recording", self.frame)
        if self.frame is None:
            print("frame no exist?")
            return
        self.writer.write(self.frame)

    def stop_recording(self):
        if self.writer is None:
            return
        cv2.destroyWindow("Recording")
        self.writer.release()
        self.writer = None

class AudioRecorder:
    def __init__(self, chunk_size, format, channels, rate):
        self.chunk_size = chunk_size
        self.format = format
        self.channels = channels
        self.rate = rate
        self.frames = []
        self.start_recording()

    def start_recording(self):
        self.p = pa.PyAudio()
        self.stream = self.p.open(
            format = self.format,
            channels = self.channels,
            rate = self.rate,
            input = True,
            frames_per_buffer = self.chunk_size
        )

    def write_frame(self, path):
        self.path = path
        if self.path is None:
            return
        if self.stream is None:
            return
        self.data = self.stream.read(self.chunk_size)
        self.frames.append(self.data)
        self.wf = wave.open(self.path, 'wb')
        self.wf.setnchannels(self.channels)
        self.wf.setsampwidth(pa.PyAudio().get_sample_size(self.format))
        self.wf.setframerate(self.rate)
        self.wf.writeframes(b''.join(self.frames))

    def stop_recording(self):
        self.wf.close()
        self.frames = []


class Processing:
    def __init__(self, video_path, s_path, audio_path, end_path, image_path):
        self.audio = audio_path
        self.video = video_path
        self.slowed = s_path
        self.end = end_path
        self.image = image_path
    
    def video_produce(self):
        cmd = "ffmpeg -i "+ self.video + " -filter:v \"setpts=2.5*PTS\" " + self.slowed
        subprocess.call(cmd, shell=True)
        print("Slowed video down to correct frame rate")
        self.dir = os.getcwd()
        temp = open(self.end,"w")
        temp.close()
        cmd = "ffmpeg -y -i " + self.audio + " -r 30 -i " + self.slowed + " -filter:a aresample=async=1 -c:a flac -strict -2 -c:v copy " + self.end
        subprocess.call(cmd, shell=True)                                     # "Muxing Done
        print("Muxed video and audio together...")
        self.clear_files()

    def clear_files(self):
        print("Clearing unneeded files...")
        os.chdir(self.dir)
        os.remove(self.audio)
        os.remove(self.video)
        os.remove(self.slowed)
        os.remove(self.image)


class Uploading:
    def __init__(self, aws_pub, aws_sec, bucket_name, region):
        self.bucket = bucket_name
        self.pub = aws_pub
        self.sec = aws_sec
        self.region = region
        self.cred = { 
            'aws_access_key_id': self.pub,
            'aws_secret_access_key': self.sec
        }
        self.s3 = boto.client('s3', self.region, **self.cred)
        self.s3_trans = S3Transfer(self.s3)

    def upload_video(self, vid_path, vid_title):
        self.path = vid_path
        self.title = vid_title
        self.s3_trans.upload_file(self.path, self.bucket,  self.title, 
                    extra_args={'ACL': 'public-read', 'ContentType': 'video/mp4'})
        #https://"bucket_name".s3."region".amazonaws.com/"filename"
        self.s3_url = str("https://" + self.bucket + ".s3." + self.region + ".amazonaws.com/" + self.title)


class DeleteBackups:
    def __init__(self, folder, days):
        self.days = days
        self.folder = folder

    def is_old(self):
        current_time = time.time()
        list_files = os.listdir()
        for i in list_files:
            file = os.path.join(os.getcwd(),i)
            file_time = os.stat(file).st_mtime
            if(file_time < current_time - self.days):
                    print("Deleted old files, exceeded provided number of days")
                    os.remove(file)

    def delete_files(self):
        self.path_og = os.getcwd()
        os.chdir(self.folder)
        self.is_old()
        os.chdir(self.path_og)

