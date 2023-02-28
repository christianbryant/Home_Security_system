import cv2
import wave
import pyaudio as pa
import subprocess
import os
from datetime import datetime

class VideoRecorder:
    def __init__(self, width, height, fps):
        self.width = width
        self.height = height
        self.fps = fps

    def get_time(self):
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
        self.path = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-v" + ".mp4"
        self.audio_path = curr_time_wav = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + ".wav"
        self.slowed_path = slowed_name = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + "-s" + ".mp4"
        self.end_path = file_name = str(datetime.now().year) + "-" + month + "-" +  day + "_" + hour + "-" + minute + ".mp4"

    def start_recording(self):
        self.get_time()
        self.writer = cv2.VideoWriter(self.path, cv2.VideoWriter_fourcc(*'MP4V'), 30, (2560,1440))

    def stop_recording(self):
        if self.writer is None:
            return
        self.writer.release()

class AudioRecorder:
    def __init__(self, path, chunk_size, format, channels, rate):
        self.path = path
        self.chunk_size = chunk_size
        self.format = format
        self.channels = channels
        self.rate = rate
        self.frames = []

    def start_recording(self):
        self.p = pa.PyAudio()
        self.stream = p.open(
            format = self.format,
            channels = self.channels,
            rate = self.rate,
            input = True,
            frames_per_buffer = self.chunk_size
        )

    def write_frame(self):
        if self.stream is None:
            return
        self.data = self.stream.read(self.chunk_size)
        self.frames.append(self.data)
        wf = wave.open(self.path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(pa.PyAudio().get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        self.frames = []

    def stop_recording(self):
        if self.stream is None:
            return
        self.stream.stop_stream()
        self.stream.close()


class Processing:
    def __init__(self, video_path, s_path, audio_path, format, end_path):
        self.audio = audio_path
        self.video = video_path
        self.format = format
        self.slowed = s_path
        self.end = end_path
    
    def video_produce(self):
        cmd = "ffmpeg -i "+ self.video + " -filter:v \"setpts=2.5*PTS\" " + self.slowed
        subprocess.call(cmd, shell=True)
        print("Slowed video down to correct frame rate")
        cmd = "ffmpeg -y -i " + self.audio + " -r 30 -i " + self.slowed + " -filter:a aresample=async=1 -c:a flac -strict -2 -c:v copy " + self.end
        subprocess.call(cmd, shell=True)                                     # "Muxing Done
        print("Muxed video and audio together...")
        self.clear_files()

    def clear_files(self):
        print("Clearing unneeded files...")
        os.remove(self.audio)
        os.remove(self.video)
        os.remove(self.slowed)