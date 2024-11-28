#!/bin/bash

setup_env() {
    sudo apt update
    sudo apt install python3-dev python3-setuptools python3-pip gcc make


    pip install testresources
    pip install lgpio --only-binary :all:
    pip install Adafruit-Blinka
    pip install -r requirements.txt
}

setup_env
