from __future__ import division
import time
import picamera
from datetime import datetime
import RPi.GPIO as GPIO
import numpy as np
import csv
#import matplotlib.pylab as plt
#matplotlib.use('TkAgg')
#plt.ion()
#print (matplotlib.matplotlib_fname())
#quit()

#import matplotlib.pylab as plt

mount_dir = "ssd/recordings"

#Input recording length
rec_length = int(input("Enter recording duration (sec): "))

#Input filename to be used
out_filename = input("Enter output filename (e.g. jan_5_2017_rec1): ")

#Input recording resolution; required to be saved for intensity checks
rec_resolution = int(input("Enter recording resolution (e.g. 128): "))
with open("/media/pi/"+mount_dir+"/"+out_filename+"_n_pixels.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_resolution])

#Save rec_mode to disk and then load it independently in encoders.py
rec_mode = int(input("Enter data saving mode: 1-disk (longer); 2-memory (shorter): "))
with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_mode])


recording = True

server_pin = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(server_pin, GPIO.OUT)
GPIO.output(server_pin, False)

camera=picamera.PiCamera()
camera.led = False
#camera.iso=800
camera.rotation=90
camera.resolution = (rec_resolution, rec_resolution)
camera.framerate = 30
camera.shutter_speed = camera.exposure_speed
camera.shutter_speed = 30000

print(camera.analog_gain)
print(camera.digital_gain)

#time.sleep(2)


print ("Pre intensity: analog_gain: ", camera.analog_gain, "   digital_gai: ", camera.digital_gain)

if True:
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g
    #camera.shutter_speed = 30000

    camera.awb_gains =(1,1)

try:
    print('Align imaging (ctrl+c to exit)')
    camera.preview_fullscreen = False
    camera.preview_window=(0,0,500,500)
    camera.start_preview()
    while True:
        time.sleep(0.01)
    
except KeyboardInterrupt:
    camera.stop_preview()
    print("Done aligning")
    
if True: 
    while True:
        if ( (camera.analog_gain<=1.1) and (camera.analog_gain>=0.9)
            and (camera.digital_gain<=1.05) and (camera.digital_gain>=1)):
            camera.exposure_mode = 'off'
            break
        #if ( (camera.analog_gain<=2.1) and (camera.analog_gain>=1.9)
        #    and (camera.digital_gain<=2.6) and (camera.digital_gain>=2.4)):
##        if ( (camera.analog_gain>=2.9)
##            and (camera.digital_gain<=1.1) and (camera.digital_gain>=.9)):

        print("Analog: ", float(camera.analog_gain))
        print("Digital:", float(camera.digital_gain))
        time.sleep(0.5)



#********* INTENSITY DETECTION *********
if True:
    #Writ test_mode flag to disk (i.e. '3'); value is read in write_mode loop and intensity calibration is run
    with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
        writer=csv.writer(f)
        writer.writerow([3])

    print("Checking intensity boissss.")
    GPIO.output(server_pin, True)
    camera.start_recording("/media/pi/"+mount_dir+"/"+out_filename+".raw", format="rgb")
    camera.wait_recording(15)
    camera.stop_recording()        
    GPIO.output(server_pin, False)
    
    #Put correct rec_mode back into txt file
    with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
        writer=csv.writer(f)
        writer.writerow([rec_mode])

print ("Post intensity setting: analog_gain: ", camera.analog_gain, "   digital_gai: ", camera.digital_gain)

#******** START RECORDING *********

if recording:

    print("Recording boissss.")
    GPIO.output(server_pin, True)
    camera.start_recording("/media/pi/"+mount_dir+"/"+out_filename+".raw", format="rgb")
    camera.wait_recording(rec_length)
    camera.stop_recording()        
    GPIO.output(server_pin, False)




