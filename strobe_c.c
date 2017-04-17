// COMPILE: 
//gcc -o output led_trigger.cpp

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <inttypes.h>
#include <unistd.h>
#include <time.h> 

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

#include "GPIOlowlevel.h"

#define MM_CSI0_BASE    0x3F800000 // UNICAM 0
#define MM_CSI1_BASE    0x3F801000 // UNICAM 1

#define CLK_BASE        0x3f003000

#define RPI_PAGE_SIZE           4096
#define RPI_BLOCK_SIZE          4096

static int mmap_fd;
uint32_t volatile * unicam_base;

bcm_peripheral gpio;

//Pin assignment
int pinBit_blue;
int pin_blue = 12;             //#
int pinBit_short_blue;
int pin_short_blue = 26;        //26 is short blue                //#13 does not work

unsigned long long led_start_gpu_time, temp_gpu_time;
long j, k;

int unicam_open() {
    void* mmap_result;
    
    //printf ("...memory maping...\n");
    mmap_fd = open("/dev/mem", O_RDWR | O_SYNC);
   
    if (mmap_fd < 0) {
        printf("Error while openning /dev/mem\n");
        return -1;
    }
   
    mmap_result = mmap(
        NULL
      , RPI_BLOCK_SIZE
      , PROT_READ | PROT_WRITE
      , MAP_SHARED
      , mmap_fd
      , CLK_BASE
    );
   
  
    if (mmap_result == MAP_FAILED) {
        close(mmap_fd);
        printf("Error while mapping memory");
        return -1;
    }

    unicam_base = (uint32_t volatile *) mmap_result;

    return 0;
}
//***************************************************************
//*********************** LED TRIGGERING LOOP *******************
//***************************************************************
void trigger_led(int index, int led_duration) {
    
    //printf("LED FUNCTION");
    if (index) {
        //ON
        *(gpio.addr  + 7) =pinBit_blue;
        //Compute delay and wait
        //usleep(led_duration);
        
        //NB: THIS FUNCTION WAITS LED_DURATION time from the ON light - NOT from the beginning of the frame...
        //record start of led using gpu time
        led_start_gpu_time = unicam_base[2];  
        led_start_gpu_time = led_start_gpu_time<<32;      
        led_start_gpu_time = led_start_gpu_time + unicam_base[1];     //add base values of 32 bit chunk
        temp_gpu_time = led_start_gpu_time;
        while ((temp_gpu_time-led_duration)<led_start_gpu_time) {
            k=0;
            for (j=0;j<1000;j++) {
                k=k+1;
            }
            temp_gpu_time = unicam_base[2];  
            temp_gpu_time = temp_gpu_time<<32;      
            temp_gpu_time = temp_gpu_time + unicam_base[1];     //add base values of 32 bit chunk
        }
            
        //OFF
        *(gpio.addr + 10) =pinBit_blue;
        //printf("BLUE\n");
    }
    
    else {
        //ON
        *(gpio.addr  + 7) =pinBit_short_blue;
        //Compute delay and wait
        led_start_gpu_time = unicam_base[2];  
        led_start_gpu_time = led_start_gpu_time<<32;      
        led_start_gpu_time = led_start_gpu_time + unicam_base[1];     //add base values of 32 bit chunk
        temp_gpu_time = led_start_gpu_time;
        while ((temp_gpu_time-led_duration)<led_start_gpu_time) {
            k=0;
            for (j=0;j<1000;j++) {
                k=k+1;
            }
            temp_gpu_time = unicam_base[2];  
            temp_gpu_time = temp_gpu_time<<32;      
            temp_gpu_time = temp_gpu_time + unicam_base[1];     //add base values of 32 bit chunk
        }
        //OFF
        *(gpio.addr + 10) =pinBit_short_blue;
        //printf("SHORT-BLUE\n");
    }
    //usleep(int(ave-useconds));  //Sleep additional time to wait for cycle to finish; IS THIS CORRECT?!
}

//******************************************************
//***********************  MAIN LOOP *******************
//******************************************************

int strobe_c(volatile long long unsigned *gpu_last_frame) {
//void strobe_c(int num_numbers, volatile int *numbers) {

    printf ("...starting C strobing...\n");
    //printf ("...last frame in: %llu\n", gpu_last_frame[0]);
    
    pinBit_blue  =  1 <<  pin_blue;
    pinBit_short_blue = 1 << pin_short_blue;
    gpio.addr_p = GPIO_BASE; 
    if(map_peripheral(&gpio, IFACE_DEV_GPIOMEM) == -1) 
    {
        printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
        return 1;
    }
 
    // initialize pins for output
    *(gpio.addr + (pin_blue/10)) &= ~(7<<((pin_blue %10)*3));
    *(gpio.addr + (pin_blue/10)) |=  (1<<((pin_blue%10)*3));
    *(gpio.addr + (pin_short_blue/10)) &= ~(7<<((pin_short_blue %10)*3));
    *(gpio.addr + (pin_short_blue/10)) |=  (1<<((pin_short_blue%10)*3));
        
    // GENERATE Memory mapping
    //printf("Openning unicam 1...\n");
    if (unicam_open() == -1) {
      printf("Openning unicam failed\n");
      return 1;
    }

    // Load inter-frame-interval (this comes based on experience dealing with picam; migth be worth exploring more)
    FILE *o; 
    float ave_ifi;   
    o = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_ave_ifi.txt", "r");
    fscanf(o, "%10f", &ave_ifi);
    printf("ave_ifi = %.8f usec\n", ave_ifi);
    fclose(o);

    //Load led ON times
    int led_duration;  
    o = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_led_duration.txt", "r");
    fscanf(o, "%i", &led_duration);
    printf("led_duration = %.5i usec\n", led_duration);
    fclose(o);
   
    //LOAD recording length in seconds
    float rec_length; 
    o = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_rec_length.txt", "r");
    fscanf(o, "%5f", &rec_length);
    printf("rec length = %.5f sec\n", rec_length);
    fclose(o);
    
    // LOOP Over strobing function
    unsigned long long gpu_time, end_time, temp_time, gpu_time_array[100000];
    unsigned long long current_frame, current_frame_array[100000], index_array[100000];
    unsigned long long temp_previous_gpu_time, previous_gpu_time=0; 
    unsigned long long previous_frame=0;

    gpu_time = unicam_base[2];  //load and bit shift nearby 32bit chunk
    gpu_time = gpu_time<<32;
    gpu_time = gpu_time + unicam_base[1];
    end_time = gpu_time + (rec_length+5)*1E6;  //end 20 seconds after python picam code finishes
    printf ("start: %llu  end: %llu\n", gpu_time, end_time);
    

    //for while (loop_var) {
    unsigned long long i,k=0;
    int index=0;
    previous_frame = gpu_last_frame[0];     //capture previous frame gpu timestamp at the time of reading gpu time;
    for (i=0; i<10000000000; ++i) {
    //int a;
    //for (a=0; a<20000000; a=a+1){
        //READ current GPU time stamp and determine what the current_frame # is
        gpu_time = unicam_base[2];  
        gpu_time = gpu_time<<32;      
        gpu_time = gpu_time + unicam_base[1];     //add base values of 32 bit chunk
        //temp_previous_gpu_time = gpu_last_frame[0];     //capture previous frame gpu timestamp at the time of reading gpu time;
        //current_frame = (gpu_time-previous_gpu_time) / ave_ifi;
        current_frame = (gpu_time-previous_gpu_time)/ave_ifi;
        
        //printf ("%llu %llu %llu %llu\n", gpu_time, previous_gpu_time, current_frame, previous_frame);

        //TRIGGER lights/printout statements if new frame is detected
        if (current_frame>0){ //(current_frame-led_duration) > previous_frame) {
            //printf ("%llu %llu %llu \n", gpu_time, previous_gpu_time, gpu_time-previous_frame);
            //printf ("... memory, computed, diff: %llu %llu %llu\n", gpu_last_frame[0], previous_frame, gpu_last_frame[0]-previous_frame);
            
            ////Trigger leds
            trigger_led(index%2, led_duration);
            previous_frame=gpu_time;

            ////Save data in arrays - to be saved to disk later
            gpu_time_array[index] = gpu_time;
            current_frame_array[index] = current_frame;
            index_array[index]=index%2;
            index=index+1;
            
            //////Every second read last frame time and reset alignment of LED flashes
            //if ((current_frame%60)==0){
                //previous_frame=0;
                //previous_gpu_time = gpu_last_frame[0]; //Capture gpu clock of most recent frame
            
                ////Exit when going overtime
            //}
            
            //WAIT HERE UNTIL time expired
            while (((gpu_time-previous_gpu_time)/ave_ifi)<0) {
                k=0;
                for (j=0;j<100000;j++) {k=k+1;}
                gpu_time = unicam_base[2];  
                gpu_time = gpu_time<<32;      
                gpu_time = gpu_time + unicam_base[1];     //add base values of 32 bit chunk
                //usleep(10);
            }
            previous_gpu_time=gpu_last_frame[0];

            if (gpu_time>end_time) break;
        }
    }
    printf("...Saving led times in C...");
    FILE *fp;                    //Not sure how many of these are still required
    fp = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_led_times.txt", "w");
    for (j=0; j<(index+1); ++j) {
        fprintf(fp, "%llu %llu %llu\n", gpu_time_array[j], current_frame_array[j], index_array[j]);
    }
    fclose(fp);
    
    printf ("...done...\n");
    return 0;
}
