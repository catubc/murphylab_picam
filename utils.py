from __future__ import division
import time
import picamera
from datetime import datetime
import RPi.GPIO as GPIO
import numpy as np
import csv, os
#from concurrent.futures import ThreadPoolExecutor
from picamera import mmal, mmalobj as mo


def strobe(camera_obj):
    #frame_length = 1E6/camera_obj.rec_rate     #33333        #Frame length in milliseconds
    print ("... processing mmal...")
    led_lights = ['green', 'blue ']

    #Setup pins
    pin_orange = 13     #26 is short blue; 12 is blue
    pin_red = 12         #12 works; 13 does not
    
    pins = [pin_orange, pin_red]
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin_red, GPIO.OUT)
    GPIO.setup(pin_orange, GPIO.OUT)
    
    GPIO.output(pin_red, False)
    GPIO.output(pin_orange, False)
    
    #save params in a large file
    params = []

    #Wait for first second worth of frames to be written to disk
    t_wait = 4*(30/camera_obj.rec_rate)+0.5
    print ("...waiting: ", t_wait, " for 30 frame times to be written: ", camera_obj.first_100_frames_filename)
    time.sleep(t_wait)
    
    #Load frames from disk
    if os.path.exists(camera_obj.first_100_frames_filename):
        first_times = np.loadtxt(camera_obj.first_100_frames_filename)
    else:
        print ("...intial frame times not found ...")
    
    t0 = np.int64(first_times[10])
    print ('....first frame time: ', t0)
    
    intervals = first_times[5:]-first_times[4:-1]
    frame_length = np.mean(intervals)
    print ('....inter frame interval: ', frame_length, " usec")
    
    ##Convert GPU time to time.time
    #for k in range(1500):
    #    t_real1 = time.clock()
    #    t_gpu = camera_obj.control.params[mmal.MMAL_PARAMETER_SYSTEM_TIME]
    #    t_real2 = time.clock()
    #    t_gpu_delta = (t_gpu - t0)*1.0E-6 - (t_real2-t_real1)
    #    t_real0 = t_real1 - t_gpu_delta
    
    #    print (t_real0, t_real2, t_real2-t_real0, t0, t_gpu, t_gpu_delta, t_real2-t_real1)
    
    #quit()
    
    ##Match GPU clock to t_real
    #t_real_initial = time.clock()
    #t_gpu = camera_obj.control.params[mmal.MMAL_PARAMETER_SYSTEM_TIME]
    #t_real = time.clock()
    #next_frame_delta = (t_gpu - t0)/float(frame_length) - int((t_gpu - t0)/float(frame_length))
    #next_frame_time = t_real + next_frame_delta*frame_length*1.0E-6
        
    #This loop could be done in C if necessary
    next_frame = 0
    ctr = 0
    while True:
        t1 = camera_obj.control.params[mmal.MMAL_PARAMETER_SYSTEM_TIME]
        
        #t1 = time.clock()
        
        if t1>next_frame:
            #print ("... new frame: ", t1)
            GPIO.output(pins[(ctr)%2], True)
            time.sleep(0.008)    #Stay on for a period of time - 1ms
            GPIO.output(pins[ctr%2], False)
            
            #OPTIONAL PRINT STATEMENTS
            #frame_time = int(t0+current_frame*frame_length)
            #print ("frame: ", current_frame, led_lights[current_frame%2], 
            #    "  ~GPU time: ", frame_time, "  LED time: ", t1, 
            
            current_frame = next_frame
            print (" Light on post frame: ", t1-current_frame, "usec")
            #params.append([current_frame, current_frame%2, frame_time, t1, t1-frame_time])

            ctr+=1
            next_frame = int(t0 + frame_length*ctr)      #Compute next frame ahead of time to make loop calculations even simpler
            
            #next_frame_time = next_frame_time + frame_length*1E-6 TRY THIS AGAIN WITH A COUNTER

            ####Check to see if reached end of recording
            #if (t1-t0)>camera_obj.rec_length*1E6: 
                
                #for pin in pins:
                    #GPIO.output(pin, False)

                #print (params)
                ##np.savetxt(camera_obj.first_100_frames_filename[:-4]+"_params.txt", np.int64(params))

                #break     #No need to check this every loop; just do it after a frame is saved
