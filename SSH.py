import RPi.GPIO as GPIO
import time
from datetime import datetime
import random
import json

# Code for LED/Gas Detector of MQ9
MQ9_DO_PIN = 17
LED_PIN_NORMAL = 25

# Setup GPIO
GPIO.setwarnings(False)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setup(MQ9_DO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN_NORMAL, GPIO.OUT)

LOW_THRESHOLD = 50
HIGH_THRESHOLD = 400

# Path to save JSON data
JSON_PATH = '/var/www/html/co2sensor/co2_data.json'

def get_gas_concentration():
    return random.randint(0, 600)

def flash_warning_led(times=3, interval=0.5):
    for _ in range(times):
        GPIO.output(LED_PIN_NORMAL, GPIO.LOW)
        time.sleep(interval)
        GPIO.output(LED_PIN_NORMAL, GPIO.HIGH)
        time.sleep(interval)

def write_to_json(data):
    with open(JSON_PATH, 'w') as f:
        json.dump(data, f)

try:
    while True:
        concentration = get_gas_concentration()
        mq9_value = GPIO.input(MQ9_DO_PIN)

        detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        status = "No gas detected"
        if mq9_value == GPIO.LOW:
            if concentration >= HIGH_THRESHOLD:
                status = f"Critical gas level detected! (≥ 400 ppm)"
                flash_warning_led(times=3, interval=0.2)
                GPIO.output(LED_PIN_NORMAL, GPIO.HIGH)
            elif concentration >= LOW_THRESHOLD:
                status = f"Warning: Gas detected! (50-400 ppm)"
                flash_warning_led(interval=0.5)
                GPIO.output(LED_PIN_NORMAL, GPIO.HIGH)
            else:
                status = "No significant gas detected"
                GPIO.output(LED_PIN_NORMAL, GPIO.LOW)
        else:
            GPIO.output(LED_PIN_NORMAL, GPIO.LOW)

        data = {
            "timestamp": detection_time,
            "concentration": concentration,
            "status": status
        }
        write_to_json(data)
        print(f"{status} at {detection_time}. Concentration: {concentration} ppm")

        time.sleep(2)

except KeyboardInterrupt:
    print("Program stopped by user.")
finally:
    GPIO.output(LED_PIN_NORMAL, GPIO.LOW)
    GPIO.cleanup()

