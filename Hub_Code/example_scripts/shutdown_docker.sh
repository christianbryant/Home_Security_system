#!/bin/bash
echo "Stopping and removing current docker images/containers"
docker stop pihub && docker container rm pihub && docker image rm hubcode
echo "Success"