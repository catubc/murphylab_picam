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

int pinBit ;
int pin_blue = 12;             //#26 is short blue; 12 is blue
int pin_short_blue = 26;                //#12 works; 13 does not
    
int pin = pin_blue;
int ctr=0;

int useconds = 14000;
FILE *fp;       //MUST BE GLOBAL
FILE *myFile;

char line[256]; 
char file_name[] = "/media/pi/2AA09E4DA09E1F7F/recs/test_999.raw_latest_frame.txt"; //GLOBAL deals with file inside function
int i;
unsigned long long frame_time;
unsigned long previous_gpu_time=0; 
unsigned long long previous_frame=0;
    
int unicam_open() {
    void* mmap_result;
   
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

void trigger_led(unsigned long long current_frame, unsigned long long temp_time) {
      
    //if ((temp_time-current_frame*ave)>1) {
    //     printf ("%f\n", temp_time-current_frame*ave);
    //}
    fprintf(fp, "%llu %llu\n", temp_time, current_frame);
    
    //else {
    //     printf ("** %f\n", temp_time-current_frame*ave);
    //}
    
    
    if (ctr%2 == 0) {
        //ON
        *(gpio.addr  + 7) =pinBit;
        //Compute delay and wait
        usleep(useconds);

        //OFF
        *(gpio.addr + 10) =pinBit;
    }
    ctr = ctr+1;

}


//******************************************************
//***********************  LOAD LATEST FRAME TIME LOOP *********
//******************************************************
void read_current_frame(double ave) {

    myFile = fopen(file_name, "r"); //open file for reading
    
    //CONVERT raw frametimes to integer for computation below
    while (fgets(line, sizeof(line), myFile)) {
    //for (i=0; i<100; ++i) {
        frame_time = strtoull(line, NULL, 0);
        //int result = _atoi64(line);
        //printf("%llu\n", result);
        //printf("%i %llu \n", i, frame_time[i]);
        i++;
    }
    fclose(myFile);
    
    printf ("Loaded GPU time : %llu\n", frame_time);
    printf ("...frame no.: %d\n", int(frame_time/ave));
    previous_gpu_time = frame_time;
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



int main() {

    pinBit  =  1 <<  pin;
    gpio.addr_p = GPIO_BASE; 
    if(map_peripheral(&gpio, IFACE_DEV_GPIOMEM) == -1) 
    {
        printf("Failed to map the physical GPIO registers into the virtual memory space.\n");
        return 1;
    }
    
 
    // initialize pin for output
    *(gpio.addr + (pin/10)) &= ~(7<<((pin %10)*3));
    *(gpio.addr + (pin/10)) |=  (1<<((pin%10)*3));
    
    
    // GENERATE Memory mapping
    printf("Openning unicam 1...\n");
    if (unicam_open() == -1) {
      printf("Openning unicam failed\n");
      return 1;
    }

    //*********** GENERATE TIME STAMPS FROM DISK **************
    // LOAD data file from disk;

    double ave;
    int new_frame=0;
    //int ifi[100];
    
    ave = 16611.25;
    
    printf ("Average interframe interval:%f \n", ave);

   
    //***************** WHILE LOOP WAITING FOR NEXT FRAME **********************
    //Open file for saving 
    fp = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_led_times.txt", "w");

    unsigned long long temp_time, current_frame;
    while (1) {
    //int a;
    //for (a=0; a<20000000; a=a+1){
        //READ current GPU time stamp and determine what the current_frame # is
        temp_time = unicam_base[1];  //Offset GPU time by latest info on previous frame_time; Helps with Drift
        current_frame = (temp_time-previous_gpu_time) / ave;
        
        //TRIGGER lights/printout statements if new frame is detected
        if (current_frame > previous_frame) {
            printf ("%llu %llu %llu\n", temp_time, previous_gpu_time, current_frame);
            trigger_led(current_frame, temp_time);
            previous_frame=current_frame;

            if ((current_frame%60)==0){
                read_current_frame(ave);
                previous_frame=0;
            }
        }

    }
    
    fclose(fp);
    
   return 0;
}
