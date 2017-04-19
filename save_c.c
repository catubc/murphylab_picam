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

int save_c(volatile unsigned long *save_block, volatile unsigned long *frame_ctr, 
           volatile unsigned char *image_stack_0, volatile unsigned char *image_stack_1) {
//int save_c(volatile unsigned long *frame_ctr, volatile unsigned char *image_stack) {
//int save_c(volatile unsigned long *frame_flag, volatile unsigned long *frame_ctr, volatile unsigned char *image_stack) {
//int save_c(volatile unsigned long *frame_ctr, volatile u_int8_t *image_stack) {

    //image_stack = [2][100][196608] for 100 frames of 256 x 256 

    FILE *f  = fopen("/media/pi/2AA09E4DA09E1F7F/recs/test_999_c_raw.raw", "ab");
    printf ("...opening save file in C ...\n");
    int i, j, remainder_frames, stack_index=0;
    int k=0;
    unsigned long frame_index;
    while(1) {
        if (frame_ctr[0]>10) {                //DO NOT START SAVING RIGHT AWAY...WAIT for first chunk to be loaded
            frame_index = frame_ctr[0];
            if ((frame_index%save_block[0])==0) {     //CAREFUL as this index may be missed during a long save; use >=
                stack_index=((frame_index/save_block[0])%2+1)%2;  //SAVE PREVIOUS STACK NOT CURRENT ONE
                printf("Saving block: %i   starting frame %lu \n", stack_index, frame_index);
                if (stack_index==0) {
                    fwrite((const void * __restrict__)image_stack_0, sizeof(unsigned char), 196608*save_block[0], f);
                }
                else {
                    fwrite((const void * __restrict__)image_stack_1, sizeof(unsigned char), 196608*save_block[0], f);
                }
            }
        }
        
        if (frame_ctr[1]==1) {     //Python exit flag detected. save the rest of the data and exit
            printf ("%lu  %lu\n", frame_ctr[0], frame_ctr[1]);
            stack_index=(stack_index+1)%2;      //flip to next stack and save the remainder of the data; THIS DATA WILL NOT BE PERFECT
            remainder_frames=frame_ctr[0]%save_block[0];
            
            if (stack_index==0){
                for (i=0; i<remainder_frames; i++) {
                    fwrite((void *)&image_stack_0[i], sizeof(unsigned char), 196608, f);
                }
            }
            else {
                for (i=0; i<remainder_frames; i++) {
                    fwrite((void *)&image_stack_1[i], sizeof(unsigned char), 196608, f);
                }
            }
            break;
        }
        k=0;
        for (j=0;j<100000;j++) {k=k+1;}
        //usleep(16611);// GET RID OF ME *********************************************
    }

    fclose(f);

    printf ("...done saving C...\n");
    return 0;
}
