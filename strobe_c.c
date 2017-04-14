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

int pinBit_blue;
int pin_blue = 12;             //#
int pinBit_short_blue;
int pin_short_blue = 26;        //26 is short blue                //#13 does not, 12 does not
    
//int pin = pin_blue;
int led_ctr=0;

int useconds = 15000;
FILE *fp, *fp_2;       //MUST BE GLOBAL
FILE *file_name_current_frame;

char line[256]; 
char file_name[] = "/media/pi/2AA09E4DA09E1F7F/recs/test_999.raw_latest_frame.txt"; //GLOBAL deals with file inside function
unsigned long long i;
unsigned long long frame_time;
unsigned long long previous_gpu_time=0; 
unsigned long long previous_frame=0;

float rec_length; 

int unicam_open() {
    void* mmap_result;
    
    printf ("...memory maping...");
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

//void trigger_led(unsigned long long current_frame, unsigned long long temp_time) {
void trigger_led() {
          
    if (led_ctr%2 == 0) {
        //ON
        *(gpio.addr  + 7) =pinBit_blue;
        //Compute delay and wait
        usleep(useconds);
        //OFF
        *(gpio.addr + 10) =pinBit_blue;
        //printf("BLUE\n");
    }
    
    else {
        //ON
        *(gpio.addr  + 7) =pinBit_short_blue;
        //Compute delay and wait
        usleep(useconds);
        //OFF
        *(gpio.addr + 10) =pinBit_short_blue;
        //printf("SHORT-BLUE\n");
    }
    
    led_ctr = led_ctr+1;

}


//******************************************************
//***********************  LOAD LATEST FRAME TIME LOOP *********
//******************************************************
void read_current_frame(double ave) {

    //file_name_current_frame = fopen(file_name, "r"); //open file for reading
    
    ////CONVERT raw frametimes to integer for computation below
    //while (fgets(line, sizeof(line), file_name_current_frame)) {
    ////for (i=0; i<100; ++i) {
        //frame_time = strtoull(line, NULL, 0);
        ////int result = _atoi64(line);
        ////printf("%llu\n", result);
        ////printf("%i %llu \n", i, frame_time[i]);
        //i++;
    //}
    //fclose(file_name_current_frame);
    //printf ("Reading current frame\n");
    fp_2 = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999.raw_latest_frame.txt", "r");
    fscanf(fp_2, "%llu\n", &previous_gpu_time);
    fclose(fp_2);
    
    printf ("....previous GPU time: %llu\n", previous_gpu_time);
    
    
    //printf ("Loaded GPU time : %llu\n", frame_time);
    //printf ("...frame no.: %d\n", int(frame_time/ave));
    //previous_gpu_time = frame_time;
    //COMPUTE PREVIOUS FRAME
    
    //return 0;
    
    //printf ("Number of frames refreshed: %d \n", i);
    
    ////COMPUTE AVERAGE inter frame interval for interpolation of all frame times
    //sum=0;
    //for(i = 30; i < 99; ++i) {
        //ifi[i] = frame_time[i+1]-frame_time[i];
        //sum = sum+ifi[i];
        //printf("%i %d \n ", i, ifi[i]);
    //}
    //printf ("%f", sum);
    //double ave = sum/69.;

}
//******************************************************
//***********************  MAIN LOOP *******************
//******************************************************

int strobe_c(volatile long long unsigned *gpu_last_frame) {
//void strobe_c(int num_numbers, volatile int *numbers) {

    printf ("...starting c strobing...");
    printf ("...last frame in: %llu\n", gpu_last_frame[0]);
    
    pinBit_blue  =  1 <<  pin_blue;
    pinBit_short_blue = 1 << pin_short_blue;
    gpio.addr_p = GPIO_BASE; 
    if(map_peripheral(&gpio, IFACE_DEV_GPIOMEM) == -1) 
    {
        printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
        return 1;
    }
 
    // initialize pin for output
    *(gpio.addr + (pin_blue/10)) &= ~(7<<((pin_blue %10)*3));
    *(gpio.addr + (pin_blue/10)) |=  (1<<((pin_blue%10)*3));
    *(gpio.addr + (pin_short_blue/10)) &= ~(7<<((pin_short_blue %10)*3));
    *(gpio.addr + (pin_short_blue/10)) |=  (1<<((pin_short_blue%10)*3));
        
    // GENERATE Memory mapping
    printf("Openning unicam 1...\n");
    if (unicam_open() == -1) {
      printf("Openning unicam failed\n");
      return 1;
    }

    // DEFINE inter-frame-interval (this comes based on experience dealing with picam; migth be worth exploring more
    double ave = 16611.26; //60Hz inter frame interval values;
    printf ("Average inter-frame-interval:%f \n", ave);
   
    //LOAD recording length in seconds
    FILE *o;    
    o = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_rec_length.txt", "r");
    fscanf(o, "%5f", &rec_length);
    printf("rec length = %.5f sec\n", rec_length);
    fclose(o);
    
    // LOOP Over strobing function
    unsigned long long temp_time, end_time, temp_time_array[100000];
    unsigned long long current_frame, current_frame_array[100000];

    temp_time = unicam_base[2];  //bit shift nearby 
    temp_time = temp_time<<32;
    temp_time = temp_time + unicam_base[1];
    end_time = temp_time + (rec_length+5)*1E6;  //end 20 seconds after python picam code finishes
    printf ("start: %llu  end: %llu\n", temp_time, end_time);
    

    //for while (loop_var) {
    unsigned long index = 0; 
    for (i=0; i<100000000000; ++i) {
    //int a;
    //for (a=0; a<20000000; a=a+1){
        //READ current GPU time stamp and determine what the current_frame # is
        temp_time = unicam_base[2];  //bit shift nearby 
        temp_time = temp_time<<32;
        temp_time = temp_time + unicam_base[1];
        current_frame = (temp_time-previous_gpu_time) / ave;
        
        //printf ("%llu %llu %llu %llu\n", temp_time, previous_gpu_time, current_frame, previous_frame);
        //TRIGGER lights/printout statements if new frame is detected
        if (current_frame > previous_frame) {
            //printf ("%llu %llu %llu %llu\n", temp_time, previous_gpu_time, current_frame, previous_frame);
            printf ("...last frame in: %llu\n", gpu_last_frame[0]);

            //Save data in arrays - to be saved to disk later
            temp_time_array[index] = temp_time;
            current_frame_array[index] = current_frame;
            index=index+1;
            ////Trigger leds
            trigger_led();
            previous_frame=current_frame;

            //Load latest frame from disk every X seconds
            if ((current_frame%3670)==0){
                fp_2 = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999.raw_latest_frame.txt", "r");
                fscanf(fp_2, "%llu\n", &previous_gpu_time);
                fclose(fp_2);
                
                printf ("....previous GPU time: %llu\n", previous_gpu_time);
    
                //read_current_frame(ave);
                previous_frame = 0;
            }

            if (temp_time>end_time){
                break;
            }
        }
    }
    printf("...Saving led times...");
    fp = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_led_times.txt", "w");
    for (i=0; i<(index+1); ++i) {
        fprintf(fp, "%llu %llu\n", temp_time_array[i], current_frame_array[i]);
    }
    fclose(fp);
    
    printf ("Clean exit\n");
    return 0;
}
