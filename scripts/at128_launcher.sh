#!/bin/bash

if [ "$#" -ne 4 ]; then
    echo "USAGE at128Launcher.sh  SENSOR_NAME  SENSOR_TIME  TARGET_FILE  DST_FOLDER"
    exit 1
fi

SENSOR_NAME="$1"
SENSOR_TIME="$2"
TARGET_FILE="$3"
DST_FOLDER="$4"

./tools/pcl_tool ${SENSOR_NAME} ${SENSOR_TIME} ${TARGET_FILE} ${DST_FOLDER}

#CONTAINER_ID=$(docker ps | grep at128-lidar-cpp | awk '{print $1}')
#CONTAINER_ID=$(docker ps | grep extract-transform-load-<TAG>-at128 | awk '{print $1}')

#docker exec -i ${CONTAINER_ID} /cpp/PandarSwiftTest ${SENSOR_NAME} ${SENSOR_TIME} ${TARGET_FILE} ${DST_FOLDER}