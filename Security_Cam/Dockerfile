# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY requirements.txt .
COPY information.json .
RUN apt-get update && apt-get install -y build-essential portaudio19-dev

# Install packages for video and audio access, as well as the missing libraries
RUN apt-get install -y v4l-utils alsa-utils libgl1-mesa-glx libglib2.0-0 pulseaudio

# Install any other dependencies you may need

RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt

# Set the working directory in the container
WORKDIR /app

# Copy your application code into the container
COPY . /app

# Create a non-root user with an explicit UID and add permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app

# Allow access to webcam and audio devices
RUN usermod -a -G video,audio appuser

# Set up PulseAudio configuration and start the PulseAudio server
USER appuser
RUN mkdir -p ~/.config/pulse
RUN echo "default-server = unix:/tmp/pulse/native" > ~/.config/pulse/client.conf
RUN pulseaudio --start

LABEL org.opencontainers.image.authors="bryantvc@oregonstate.edu"

# During debugging, this entry point will be overridden.
CMD ["python", "main.py"]
