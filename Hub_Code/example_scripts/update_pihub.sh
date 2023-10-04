#!/bin/bash
echo "Running docker image rebuilder script..."
echo "Stopping and removing current docker images/containers"
docker stop pihub && docker container rm pihub && docker image rm hubcode
echo "Git pulling from repo"
cd /home/jaxthepi/Desktop/Pihub/Home_Security_system
git pull
echo "Building from dockerfile"
cd /home/jaxthepi/Desktop/Pihub/Home_Security_system/Hub_Code
docker build -t hubcode .
echo "Running docker image with the following settings: --restart=always --name pihub"
docker run --restart=always --name pihub hubcode
echo "Success"
