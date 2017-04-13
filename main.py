from __future__ import division
import time
import picamera
import RPi.GPIO as GPIO
import csv
import subprocess
#from concurrent.futures import ThreadPoolExecutor
#from picamera import mmal, mmalobj as mo
#from utils import strobe

#import matplotlib.pylab as plt
#matplotlib.use('TkAgg')
#plt.ion()
#print (matplotlib.matplotlib_fname())
#quit()

#import matplotlib.pylab as plt


#*********************************************************************
#**************** GET INPUT PARAMETERS OR LOAD PRESET ****************
#*********************************************************************

#mount_dir = "52C9C2EE6A8E5C89/recs"    #SSD
mount_dir = '2AA09E4DA09E1F7F/recs'     #1TB
#mount_dir = 'recs'     #internal flash

if False:
    rec_length = int(input("Enter recording duration (sec): "))                 #Input recording length
    out_filename = input("Enter output filename (e.g. jan_5_2017_rec1): ")      #Input filename to be used
    rec_resolution = int(input("Enter recording resolution (e.g. 128): "))      #Input recording resolution; required to be saved for intensity checks
    rec_rate = int(input("Enter recording rate in HZ  (e.g. 30): "))            #Input recording rate; required to be saved for intensity checks
    rec_mode = int(input("Enter data saving mode: 1-disk (longer); 2-memory (shorter): "))      #Save rec_mode to disk and then load it independently in encoders.py

else:
    #out_filename = 'test_'+str(np.random.randint(1000))
    out_filename = 'test_999'
    rec_resolution = 256 
    rec_rate = 60
    rec_mode = 1 
    rec_length = 30/rec_rate+60
    
    subprocess.Popen("%s %s" % ('rm', '/media/pi/2AA09E4DA09E1F7F/recs/test_999*'), shell=True)
    time.sleep(0.5)

with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_length.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_length])
        
with open("/media/pi/"+mount_dir+"/"+out_filename+"_n_pixels.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_resolution])

with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_rate.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_rate])
    
with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
    writer=csv.writer(f)
    writer.writerow([rec_mode])


recording = True


#*********************************************************************
#*********************** INITIALIZE CAMERA ***************************
#*********************************************************************

server_pin = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(server_pin, GPIO.OUT)
GPIO.output(server_pin, False)

    
camera=picamera.PiCamera()
camera.led = False
#camera.iso=800
camera.rotation=0
camera.resolution = (rec_resolution, rec_resolution)
camera.framerate = rec_rate    #30
camera.shutter_speed = camera.exposure_speed

camera.shutter_speed = 15000 #10 msec ******************************************

print ("...camera.shutter_speed...", camera.shutter_speed )
camera.clock_mode = 'raw'       #This outputs absolute GPU clock time instead of Delta_time


if True:
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g
    #camera.shutter_speed = 30000

    camera.awb_gains =(1,1)


#*********************************************************************
#**************************** ALIGN CAMERA ***************************
#*********************************************************************

if False: 
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
else:
	print ('...skipping alignment...')


#*********************************************************************
#**************************** SET GAINS ******************************
#*********************************************************************

if True: 
    print(camera.analog_gain)
    print(camera.digital_gain)
    print ("Pre intensity: analog_gain: ", camera.analog_gain, "   digital_gai: ", camera.digital_gain)

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

else:
    print ('...skipping gain setting... NOT GOOD...')


#*********************************************************************
#*************************** SET INTENSITIES *************************
#*********************************************************************

if True:
    #Writ test_mode flag to disk (i.e. '3'); value is read in write_mode loop and intensity calibration is run
    with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
        writer=csv.writer(f)
        writer.writerow([3])

    print("Checking intensity boissss.")
    GPIO.output(server_pin, True)
    camera.start_recording("/media/pi/"+mount_dir+"/"+out_filename+".raw", format="rgb")
    camera.wait_recording(30)
    camera.stop_recording()        
    GPIO.output(server_pin, False)
    
    #Put correct rec_mode back into txt file
    with open("/media/pi/"+mount_dir+"/"+out_filename+"_rec_mode.txt", "wt") as f:
        writer=csv.writer(f)
        writer.writerow([rec_mode])

    print ("Post intensity setting: analog_gain: ", camera.analog_gain, "   digital_gai: ", camera.digital_gain)


#*********************************************************************
#**************************** RECORDING ******************************
#*********************************************************************

if recording:

    print("Recording boissss.")
    GPIO.output(server_pin, True)
    
    ##********* GPU CLOCK PROCESSING ***********
    #camera_obj = mo.MMALCamera()
    #camera_obj.rec_length = rec_length
    #camera_obj.rec_rate = rec_rate
    #camera_obj.first_100_frames_filename = "/media/pi/" + mount_dir + "/" + out_filename + '.raw_first_100_frames.txt'

    #if False:
        #strobe(camera_obj)

    ##************ MULTI THREAD VERSION **************
    #else: 
        #t = ThreadPoolExecutor(max_workers=1)
        #t.map(strobe, [camera_obj])
    
    camera.start_recording("/media/pi/"+mount_dir+"/"+out_filename+".raw", format="rgb")
    
    #Recompile and run C code
    #subprocess.Popen(['gcc', '-o output led_trigger.cpp'])
    time.sleep(1)
    subprocess.Popen(['sudo', './output'])


    camera.wait_recording(rec_length)
    print ("... *****************saving python data********************************...")
    camera.stop_recording()        
    
    print ("...*************** Done Saving Python data ...")

    #t.shutdown()

    #quit()
