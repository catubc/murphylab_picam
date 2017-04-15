/*  demo.c*/
#include<graphics.h> 
int main()
{
   int gd = DETECT,gm,left=0,top=0,right=100,bottom=100,x= 100,y=50,radius=25;
   initgraph(&gd,&gm,NULL);
   rectangle(left, top, right, bottom);
   circle(x, y, radius);
   bar(left + 100, top, right + 100, bottom);
   line(left - 10, top + 150, left + 410, top + 150);
   ellipse(x, y + 100, 0, 160, 100, 50);
   outtextxy(left + 100, top + 125, "C Graphics Program");

   delay(5000);
   closegraph(); 
   return 0;
}
