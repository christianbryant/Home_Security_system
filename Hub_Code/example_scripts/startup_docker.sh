#!/bin/bash
echo "Building from dockerfile"
cd /home/jaxthepi/Desktop/Pihub/Home_Security_system/Hub_Code
docker build -t hubcode .
echo "Running docker image with the following settings: --restart=always --name pihub"
docker run --restart=always --name pihub hubcode
echo "Success"
