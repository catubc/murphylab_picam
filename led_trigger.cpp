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

int useconds = 5000;

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

void trigger_led(unsigned long long current_frame, double ave, unsigned long long temp_time) {
      
    if ((temp_time-current_frame*ave)>0) {
         printf ("%f\n", temp_time-current_frame*ave);
    }
    else {
         printf ("** %f\n", temp_time-current_frame*ave);
    }
    
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

    // LOAD data file from disk;
    char ch, file_name[] = "/media/pi/2AA09E4DA09E1F7F/recs/test_999.raw_first_100_frames.txt";
    FILE *myFile;
    char line[256];
    
    int numberArray[100];

    myFile = fopen(file_name, "r"); //read file
    
    int i, j;
    i = 0;
    unsigned long long frame_time[500];

    //CONVERT raw frametimes to integer for computation below
    while (fgets(line, sizeof(line), myFile)) {
        
        frame_time[i] = strtoull(line, NULL, 0);
        
        //int result = _atoi64(line);
        //printf("%llu \n", frame_time[i]);
        
        i++;
    }
    
    printf ("Number of frames loaded: %d \n", i);
    
    //COMPUTE AVERAGE inter frame interval for interpolation of all frame times
    double sum=0;
    int ifi[500];
    for(j = 0; j < i-1; ++j)
    {
        ifi[j] = frame_time[j+1]-frame_time[j];
        sum = sum+ifi[j];
        //printf( "%d \n ", ifi[j]);
    }
    
    double ave = sum/j;
    
    printf ("Average interframe interval:%f \n", ave);

   
    //***************** WHILE LOOP WAITING FOR NEXT FRAME **********************
    unsigned long long temp_time, current_frame, previous_frame=0;
    while (1) {

        //READ current GPU time stamp and determine what the current_frame # is
        temp_time = unicam_base[1];
        current_frame = temp_time / ave;
        
        //TRIGGER lights/printout statements if new frame is detected
        if (current_frame > previous_frame) {
    
            trigger_led(current_frame, ave, temp_time);
            previous_frame=current_frame;
        }
    }
   return 0;
}
