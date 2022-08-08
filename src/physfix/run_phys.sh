#!/bin/bash
# docker run -v $1:/physfix/$1 phys /physfix/$1 --output_path $2
docker run -v "$1":"$1" phys "$2" --output_file "$3"