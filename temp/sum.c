#include <stdio.h>
#include <unistd.h>
#include <time.h>


// compile instructions: cc -fPIC -shared -o libsum.so sum.c

int c_function(int num_numbers, volatile int *numbers) {
    int i,j;
    int sum;
    int useconds = 500000;
    
    for (j=0; j<10;j++){
        printf("C:        ");
        for (i = 0; i < num_numbers; i++) {
            printf("%i ", numbers[i]);
            numbers[i]=numbers[i]*numbers[i];
        }
        usleep(useconds);
        
        printf("\n");
    }
    return 0;
}
