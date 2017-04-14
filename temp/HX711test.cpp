#include "HX711.h"

// **************************************************************************************************************
//  Gets a line of input from stdin
// Last modified 2016/06/01 by Jamie Boyd

 bool myGetline(char * line, int lenMax, int keepNewLine) {
	
	int len;
	int readVal;
	char readChar;
	for(len=0; len < lenMax; len +=1) {
		readVal = getchar(); // read next value into an int (need bigger than a char to account for EOF  -which we should never see anyways
		readChar = (char) readVal;
		line[len] =readChar;
		if ( readChar == '\n'){
			if (keepNewLine)
				len +=1;
			break;
		}
	}
	if (len == lenMax ){
		printf ("You entered too many characters on the line; the limit is %d\n", lenMax);
		return false;
	}else{
		line[len] = '\0';
		return true;
	}
}

const int kDATAPIN=23;
const int kCLOCKPIN = 24;
const float kSCALING = 7.15e-05;

int main(int argc, char **argv){
	HX711 scale = HX711 (kDATAPIN, kCLOCKPIN, kSCALING, true);
	// make a temp buffer to hold a line of text 
	int maxChars = 20;
	char * line = new char [maxChars];
	signed char menuSelect;
	float newScaling;
	printf ("Enter a number from the menu below\n");
	for (;;){
		printf ("-1:\tQuit the program.\n");
		printf ("0:\tTare the scale with 10 readings.\n");
		printf ("1\tWeigh something with 10 readings\n");
		printf ("2\tWeigh something with 1 reading\n");
		printf ("3\tSet new scaling\n");
		printf ("4\tSet scale to low power mode\n");
		printf ("5\tWake scale from low power mode\n");
		// scan the input into a string buffer
		if (myGetline(line, maxChars, 1)  == false)
			continue;
		// Get the menu selection, and check it
		sscanf (line, "%hhd\n", &menuSelect);
		if ((menuSelect < -1) || (menuSelect > 5)){
			printf ("You entered a selection, %hhd, outside the range of menu items (-1-5)\n", menuSelect);
			continue;
		} 
		switch (menuSelect){
			case -1:
				printf ("Quitting...\n");
				return 0;
				break;
			case 0:
				scale.tare (10, true);
				break;
			case 1:
				printf ("Measured Weight was %.2f grams.\n", scale.weigh (10,true));
				break;
			case 2:
				printf ("Measured Weight was %.2f grams.\n", scale.weigh (1,false));
				break;
			case 3:
				printf ("Set Scaling  (currently %.2f grams/unit)=",scale.getScaling());
				if (myGetline(line, maxChars, 1)  == false)
					break;
				sscanf (line, "%f\n", &newScaling);
				scale.setScaling (newScaling);
				break;
			case 4:
				scale.turnOFF();
				break;
			case 5:
				scale.turnON ();
				break;
		}
	}
}