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

int save_c(volatile unsigned long *frame_ctr, volatile unsigned char *image_stack) {
//int save_c(volatile unsigned long *frame_flag, volatile unsigned long *frame_ctr, volatile unsigned char *image_stack) {
//int save_c(volatile unsigned long *frame_ctr, volatile u_int8_t *image_stack) {

    //image_stack = [2][100][196608] for 100 frames of 256 x 256 

    printf ("...starting c saving code...\n");

    FILE *f  = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_c_raw.raw", "ab");
    printf ("...finished opening save file in C ...\n");
    int i, j, remainder_frames, stack_index=0;
    unsigned long frame_index;
    int n_sec =15;
    while(1) {
        if (frame_ctr[0]>10) {                //DO NOT START SAVING RIGHT AWAY...WAIT for first chunk to be loaded
            frame_index = frame_ctr[0];
            if ((frame_index%100)==0) {
                //frame_index = frame_index - 100;
                stack_index=((frame_index/100)%2+1)%2;  //SAVE PREVIOUS STACK NOT CURRENT ONE
                //stack_index = (frame_ctr[0]/500)%2;   //Determine which stack reading;
                printf("Saving stack: %i   starting frame %lu ", stack_index, frame_index);
                //for (i=0; i<100; i++) {
                    //for (j=0; j<199608; j++) {
                        //fwrite((void *)&image_stack[stack_index,i,j], sizeof(uint8_t), 1, f);
                        //fwrite((void *)&image_stack[stack_index,i,j], sizeof(char), 1, f);
                        //fwrite((void *)&image_stack[stack_index], sizeof(u_int8_t), 196608*100, f);
                        fwrite((void *)&image_stack[stack_index], sizeof(unsigned char), 196608*100, f);
                    //}
                //}
                //printf("C stack %i frame %lu:  ", stack_index, frame_index);
                printf("%i %i %i %i %i\n", image_stack[stack_index,frame_index%100,5010], image_stack[stack_index,frame_index%100,5030],
                    image_stack[stack_index,frame_index%100,5020], image_stack[stack_index,frame_index%100,5040], image_stack[stack_index,frame_index%100,5050]);
            }
            // break
        }
        if (frame_ctr[0]>(60*n_sec)) break;     //out of time - MIGHT NOT BE REQUIRED
        
        if (frame_ctr[1]==1) {     //Python exit flag detected. save the rest of the data and exit
            printf ("%lu  %lu\n", frame_ctr[0], frame_ctr[1]);
            stack_index=(stack_index+1)%2;      //flip to next stack and save the remainder of the data; THIS DATA WILL NOT BE PERFECT
            
            remainder_frames=frame_ctr[0]%100;
            
            for (i=0; i<remainder_frames; i++) {
                fwrite((void *)&image_stack[stack_index,i], sizeof(unsigned char), 196608, f);
            }
        
            break;
        }
        usleep(16611);
    }

    fclose(f);

    printf ("...done saving C...\n");
    return 0;
}
