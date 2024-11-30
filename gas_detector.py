import time
import board
import os
from busio import SPI, I2C
from digitalio import DigitalInOut 
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
import mh_z19
from pygame import mixer
import adafruit_mma8451
import psutil
import json

#Webserver: sudo service apache2 restart

# Initialize pygame mixer
mixer.init()

# Load your alarm sound (replace with your own audio file)
alarm_sound = mixer.Sound("Alarm.wav")

# Create the SPI bus
spi = SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)

# Create the cs (chip select)
cs = DigitalInOut(board.D5)  # Adjust this pin as needed

# Initialize I2C bus
i2c = I2C(board.SCL, board.SDA)

# Initialize MMA8451 accelerometer
accelerometer = None
while not accelerometer:
     try:
         accelerometer = adafruit_mma8451.MMA8451(i2c) 
         accelerometer.range = adafruit_mma8451.RANGE_8G
         print(accelerometer)
     except OSError as e:
         print(f"i2c error {e} \nretrying....")
         time.sleep(1)

# Create the mcp object
mcp = MCP.MCP3008(spi, cs)

# Create analog input channels on pin 0 (MQ-9) and pin 1 (MQ-136)
chan0 = AnalogIn(mcp, MCP.P0)  # MQ-9 for CO
chan1 = AnalogIn(mcp, MCP.P1)  # MQ-136 for H2S

def mem_usage():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"Memory used: {mem_info.rss / 1024 / 1024} Megabytes")    

def convert_to_ppm_co(voltage):
    # Adjust these values based on your MQ-9 sensor's specifications
    zero_voltage = 0.4  # voltage at 0 ppm (clean air)
    span_voltage = 2.0  # voltage at maximum ppm
    span_ppm = 1000     # maximum ppm value for your sensor

    if voltage <= zero_voltage:
        return 0
    elif voltage >= span_voltage:
        return span_ppm
    else:
        ppm = (voltage - zero_voltage) * (span_ppm / (span_voltage - zero_voltage))
        return round(ppm, 2)


def convert_to_ppm_h2s(voltage):
    # Adjust these values based on your MQ-136 sensor's specifications
    zero_voltage = 0.5  # voltage at 0 ppm (clean air)
    span_voltage = 4.0  # voltage at maximum ppm
    span_ppm = 100      # maximum ppm value for your sensor

    if voltage <= zero_voltage:
        return 0
    elif voltage >= span_voltage:
        return span_ppm
    else:
        ppm = (voltage - zero_voltage) * (span_ppm / (span_voltage - zero_voltage))
        return max(0, round(ppm, 2))

def sound_alarm(urgency):
    start_time = time.time()
    while time.time() - start_time < 30:  # Run for 30 seconds
        if urgency == "high":
            alarm_sound.play()
            time.sleep(0.2)
            alarm_sound.stop()
            time.sleep(0.1)
        elif urgency == "medium":
            alarm_sound.play()
            time.sleep(0.5)
            alarm_sound.stop()
            time.sleep(0.5)
        else:
            alarm_sound.play()
            time.sleep(1)
            alarm_sound.stop()
            time.sleep(1)
    alarm_sound.stop()

def read_accelerometer():
    x, y, z = accelerometer.acceleration
    magnitude = (x**2 + y**2 + z**2)**0.5
    return magnitude

mem_usage()

# Warm-up period
print("Warming up sensors: 1 minute. Please wait. Thank you!")
time.sleep(60)  # Sensors' warm-up time

try:
    while True:
        co_voltage = chan0.voltage
        h2s_voltage = chan1.voltage
        
        co_ppm = convert_to_ppm_co(co_voltage)
        h2s_ppm = convert_to_ppm_h2s(h2s_voltage)
        MH_Z19_data = mh_z19.read_all()
        magnitude = read_accelerometer()
        
        # Data structure for displaying the output on the webpage
        web_data = {
            'co': {"value": co_ppm, "status": ""},
            'h2s': {"value": h2s_ppm, "status": ""},
            'mhz': {"value": MH_Z19_data, "status": ""},
            'accel': {"value": magnitude, "status": ""}
        }
        
        
        
        alarm_urgency = None
        
        
        
        # Carbon Dioxide Sensor
        if 0 <= MH_Z19_data['co2'] < 4999:
            print(f"No significant Carbon Dioxide detected. PPM: {MH_Z19_data['co2']}")
            web_data["mhz"]["status"] = "No significant Carbon Dioxide detected."
             
        elif 5000 <= MH_Z19_data['co2'] < 20000:
            print(f"Significant Carbon Dioxide detected! PPM: {MH_Z19_data['co2']}")
            web_data["mhz"]["status"] = "Significant Carbon Dioxide detected!"
            alarm_urgency = "high"
        
        # Carbon Monoxide Sensor (MQ-9)
        if 0 <= co_ppm < 50:
            print(f"No significant Carbon Monoxide detected. PPM: {co_ppm}")
            web_data["co"]["status"] = "No significant Carbon Monoxide detected"
            
        elif 50 <= co_ppm < 200:
            print(f"Carbon monoxide detected! PPM: {co_ppm}")
            web_data["co"]["status"] = "Carbon monoxide detected!"
            alarm_urgency = "medium" if alarm_urgency != "high" else "high"
        else:
            print(f"Significant Carbon monoxide detected! PPM: {co_ppm}")
            web_data["co"]["status"] = "Significant Carbon monoxide detected!"
            alarm_urgency = "high"
        
        # Hydrogen Sulfide Sensor (MQ-136)
        if 0 <= h2s_ppm < 50:
            print(f"No significant Hydrogen Sulfide detected. PPM: {h2s_ppm}")
            web_data["h2s"]["status"] = "No significant Hydrogen Sulfide detected."
        elif 50 <= h2s_ppm < 200:
            print(f"Hydrogen Sulfide detected! PPM: {h2s_ppm}")
            web_data["h2s"]["status"] = "Hydrogen Sulfide detected!"
            alarm_urgency = "medium" if alarm_urgency != "high" else "high"
        else:
            print(f"Significant Hydrogen Sulfide detected! PPM: {h2s_ppm}")
            web_data["h2s"]["status"] = "Significant Hydrogen Sulfide detected!"
            alarm_urgency = "high"
        
        # Temperature Reader   
        print(f"Temperature: {MH_Z19_data['temperature']} Celsius")
        
        
        # Check for significant motion
        if magnitude >= 39.22:
            print("Warning: Possible injury")
            web_data["accel"]["status"] = "Warning: Possible Injury"
            if not alarm_urgency:
                alarm_urgency = "high"
        
        try:
            out_file = open('/var/www/html/co2_data.json', "w")
            json.dump(web_data, out_file)
                
        except Exception as e:
            web_data = {
                'error': f"There was an error: {e}"
            }
            
            out_file = open('/var/www/html/co2_data.json', "w")
            json.dump(web_data, out_file)
                
        mem_usage()
        if alarm_urgency:
            sound_alarm(alarm_urgency)
            
        
        
        time.sleep(15)
        
except KeyboardInterrupt:
    print("Program stopped by user")
    alarm_sound.stop()
    mixer.quit()
