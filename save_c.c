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


//******************************************************
//***********************  MAIN LOOP *******************
//******************************************************

int k ;

//int save_c(volatile unsigned long *frame_ctr, volatile uint8_t *image_stack) {
int save_c(volatile unsigned long *frame_ctr, volatile unsigned char*image_stack) {

    //image_stack = [2][100][196608] for 100 frames of 256 x 256 

    printf ("...starting c saving...\n");

    while(1) {
        printf("%lu %i \n", frame_ctr[0], image_stack[0,0,0]);
        //for (k=0; k<100; k++){
         //   printf("%i %s \n", k, image_stack[0,1,k]);
       // }
        //if (image_stack[0][99][0]>0):
        // break
        usleep(500000);
    }


    // Load inter-frame-interval (this comes based on experience dealing with picam; migth be worth exploring more)
    FILE *o; 

    o = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_c_raw.raw", "w");
    fclose(o);

    
    printf ("...done saving c...\n");
    return 0;
}
