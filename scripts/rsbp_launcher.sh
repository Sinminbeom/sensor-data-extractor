#!/bin/bash

if [ "$#" -ne 6 ]; then
    echo "USAGE rsbpLauncher.sh  SENSOR_NAME  SENSOR_TIME  TARGET_FILE  DST_FOLDER  MOSP_PORT  DIFOP_PORT"
    exit 1
fi

SENSOR_NAME="$1"
SENSOR_TIME="$2"
TARGET_FILE="$3"
DST_FOLDER="$4"
MOSP_PORT="$5"
DIFOP_PORT="$6"

./tools/rs_driver_pcdsaver ${SENSOR_NAME} ${SENSOR_TIME} ${TARGET_FILE} ${DST_FOLDER} ${MOSP_PORT}

# CONTAINER_ID=$(docker ps | grep extract-transform-load-<TAG>-rsbp | awk '{print $1}')

# docker exec -i ${CONTAINER_ID} /cpp/demo_pcap ${SENSOR_NAME} ${SENSOR_TIME} ${TARGET_FILE} ${DST_FOLDER} ${MOSP_PORT} ${DIFOP_PORT}