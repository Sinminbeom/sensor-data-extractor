#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "USAGE gnssLauncher.sh  TARGET_FILE  DST_FOLDER"
    exit 1
fi


TARGET_FILE="$1"
DST_FOLDER="$2"

./tools/converter_file_parser ./src/drivers/imu/messages_public.json ${TARGET_FILE} ASCII ${DST_FOLDER}

# CONTAINER_ID=$(docker ps | grep extract-transform-load-<TAG>-gnss | awk '{print $1}')

# docker exec -i ${CONTAINER_ID} /cpp/Converter_FileParser /cpp/messages_public.json ${TARGET_FILE} ASCII ${DST_FOLDER}