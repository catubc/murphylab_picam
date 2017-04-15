/*

  CURHELL2.C
  ==========
  (c) Copyright Paul Griffiths 1999
  Email: mail@paulgriffiths.net

  "Hello, world!", ncurses style (now in colour!)

*/


#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>                  /*  for sleep()  */
#include <curses.h>
#include <stdint.h>
#include <ncurses.h>

int main(void) {

    unsigned long long i = 0;
    char string_i [2];
    initscr();
    
    //scrollok(stdscr,TRUE);
    while(1) {
        itoa(i, string_i, 10);
        mvaddstr((6+i)%80, (i/100)%180, string_i);

        //usleep(10);
        ++i;
        refresh();
    }

    endwin();

    return 0;
}


