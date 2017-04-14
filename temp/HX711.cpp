#include "HX711.h"


// *********************************************************************************************
// threaded function for weighing needs to be a C  style function, not a class method
// It gets a bunch of weights as fast as possible, until array is full or thread is interrupted
// Last Modified 2016/08/16 by Jamie Boyd
extern "C" void* HX711ThreadFunc (void * tData){
	// cast tData to task param stuct pointer
	taskParams *theTask = (taskParams *) tData;
	
	 // set durations for timing for data/clock pulse length
	struct timeval durTime;
        struct timeval delayTime;
        struct timeval actualTime;
        struct timeval expectedTime;
	durTime.tv_sec = 0;
	durTime.tv_usec =1;
	delayTime.tv_sec = 0;
	delayTime.tv_usec =1;
	//give thread high priority
	struct sched_param param ;
	param.sched_priority = sched_get_priority_max (SCHED_RR) ;
	pthread_setschedparam (pthread_self (), SCHED_RR, &param) ;
	// loop forever, waiting for a request to weigh
	for (;;){
		// get the lock on getWeight and wait for weights to be requested
		pthread_mutex_lock (&theTask->taskMutex);
		while (theTask->getWeights==0)
			pthread_cond_wait(&theTask->taskVar, &theTask->taskMutex);
		//printf ("Thread was signalled.\n");
		// Unlock the mutex right away so calling thread can give countermanding signal
		pthread_mutex_unlock (&theTask->taskMutex);
		for (theTask->gotWeights =0; theTask->gotWeights < theTask->getWeights; theTask->gotWeights ++){
			// zero data array
			for (int ibit =0; ibit < 24; ibit++)
				theTask->dataArray [ibit] =0;
			// wait for data pin to go low
			while (digitalRead (theTask->dataPin) == HIGH){}
			// get data for each of 24 bits
			gettimeofday (&expectedTime, NULL);
			for (int ibit =0; ibit < 24; ibit++){
				// set clock pin high, wait dur for data bit to be set
				digitalWrite (theTask->clockPin, HIGH) ;
				timeradd (&expectedTime, &durTime, &expectedTime);
				for (gettimeofday (&actualTime, NULL); (timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
				// read data
				if (digitalRead (theTask->dataPin) == HIGH)
					theTask->dataArray [ibit] = 1;
				// set clock pin low, wait for delay period
				digitalWrite (theTask->clockPin, LOW) ;
				timeradd (&expectedTime, &delayTime, &expectedTime);
				for (gettimeofday (&actualTime, NULL); (timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
			}
			// write out another clock pulse with no data collection to set scaling to channel A, high gain
			digitalWrite (theTask->clockPin, HIGH) ;
			timeradd (&expectedTime, &delayTime, &expectedTime);
			for (gettimeofday (&actualTime, NULL); (timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
			digitalWrite (theTask->clockPin, LOW) ;
			timeradd (&expectedTime, &delayTime, &expectedTime);
			for (gettimeofday (&actualTime, NULL); (timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
			// get values for each bit set from pre-computer array of powers of 2
			theTask->weightData [theTask->gotWeights] =theTask->dataArray [0] * theTask->pow2 [0];
			for (int ibit =1; ibit < 24; ibit ++)
				theTask->weightData [theTask->gotWeights] += theTask->dataArray [ibit] * theTask->pow2 [ibit];
			theTask->weightData [theTask->gotWeights] = (theTask->weightData [theTask->gotWeights]  - theTask->tareValue) * theTask->scaling;
		}
		theTask->getWeights = 0;
	}
	return NULL;
}

HX711::HX711 (int dp, int cp, float sp, bool ip){
	dataPin = dp;
	clockPin = cp;
	scaling = sp;
	if (ip == true)
		wiringPiSetupGpio();
	pinMode (dataPin, INPUT) ; // DATA
	pinMode (clockPin, OUTPUT) ; // Clock
	digitalWrite (clockPin, LOW) ;
	// pre-compute array for value of each bit as its corresponding power of 2
	// backwards because data is read in high bit first
	for (int i=0; i<24; i++)
		pow2[i]= pow (2, (23 - i));
	pow2[0] *= -1;	// most significant bit is negative in two's complement
	// set durations for timing for data/clock pulse length
	durTime.tv_sec = 0;
	durTime.tv_usec =1;
	delayTime.tv_sec = 0;
	delayTime.tv_usec =1;
	// make a thread, for threaded reads into an array
	// be sure to point thetask.weightData to a real array before calling the threaded version
	theTask.dataPin=dataPin;
	theTask.clockPin = clockPin;
	theTask.scaling = scaling;
	 theTask.tareValue = 0;
	theTask.dataArray = dataArray;
	theTask.pow2 = pow2;
	theTask.getWeights =0;
	theTask.gotWeights=0;
	// init mutex and condition var
	pthread_mutex_init(&theTask.taskMutex, NULL);
	pthread_cond_init (&theTask.taskVar, NULL);
	// create thread
	pthread_create(&theTask.taskThread, NULL, &HX711ThreadFunc, (void *)&theTask);
}

/* takes a series of readings and stores the average value as a tare value to be
    subtracted from subsequent readings. Tare value is not scaled, but in raw A/D units*/
void HX711::tare (int nAvg, bool printVals){
    if (isPoweredUp == false)
	this->turnON ();
   
    tareValue = 0.0;
    for (int iread =0; iread < nAvg; iread++){
        tareValue += this->readValue ();
    }
    tareValue /= nAvg;
    theTask.tareValue = tareValue;
}

/* Returns the stored tare value */
float HX711::getTareValue (void){
    return tareValue;
}

/* Takes a series of readings, averages them, subtractes the tare value, and 
applies the scaling factor and returns the scaled average */
float HX711::weigh (int nAvg, bool printVals){
    if (isPoweredUp == false)
        this->turnON ();
    float readAvg =0;   
    for (int iread =0; iread < nAvg; iread++)
        readAvg += this->readValue ();
    readAvg /= nAvg;
    return ((readAvg - tareValue) * scaling);
}

/* starts the threaded version filling in a passed-in array of weight values */
void HX711::weighThreadStart (float * weights, int nWeights){
	pthread_mutex_lock (&theTask.taskMutex);
	theTask.weightData = weights;
	theTask.getWeights = nWeights;
	pthread_cond_signal(&theTask.taskVar);
	pthread_mutex_unlock( &theTask.taskMutex );
}

/* stops the threaded version and returns the number of weights so far obtained */
int HX711::weighThreadStop (void){
	theTask.getWeights = 0;
	int nWeights = theTask.gotWeights;
	theTask.gotWeights=0;
	return  nWeights;
}

/* checks how many weights have been obtained so far, but does not stop the thread */
int HX711::weighThreadCheck (void){
	return theTask.gotWeights;
}

/* Gets the saved data pin GPIO number. Note the GPIO pin can only be set
    when initialized */
int HX711::getDataPin (void){
    return dataPin;
}

/* Gets the saved clock pin GPIO number. Note the GPIO pin can only be set
    when initialized */
int HX711::getClockPin(void){
    return clockPin;
}

/* Setter and getter for scaling */
float HX711::getScaling (void){
    return scaling;
}

void HX711::setScaling (float newScaling){
	scaling = newScaling;
	theTask.scaling = scaling;
}

/* Set the clock pin high for 50ms to put the HX711 into a low power state */
void HX711::turnOFF (void){
    isPoweredUp = false;
    digitalWrite (clockPin, HIGH) ;
}

/* set the clock pin low to wake the HX711 after putting it into a low power state
wait 2 microseconds (which shuld be lots of time) to give the device time to wake */
void HX711::turnON(void){
    isPoweredUp = true;
    digitalWrite (clockPin, LOW) ;
    // wait a few microseconds before returning to give device time to wake up
   delay (2000);
}

/* reads a single value from the HX711 and returns the signed integer value 
    without taring or scaling */
int HX711::readValue (void){
    // zero data array
    for (int ibit =0; ibit < 24; ibit++){
        dataArray [ibit] =0;
    }
    // wait for data pin to go low
    while (digitalRead (dataPin) == HIGH){}
    // get data for each of 24 bits
    gettimeofday (&expectedTime, NULL);
    for (int ibit =0; ibit < 24; ibit++){
        // set clock pin high, wait dur for data bit to be set
        digitalWrite (clockPin, HIGH) ;
        timeradd (&expectedTime, &durTime, &expectedTime);
        for ( gettimeofday (&actualTime, NULL);(timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
        // read data
        if (digitalRead (dataPin) == HIGH)
            dataArray [ibit] = 1;
	// set clock pin low, wait for delay period
        digitalWrite (clockPin, LOW) ;
        timeradd (&expectedTime, &delayTime, &expectedTime);
        for ( gettimeofday (&actualTime, NULL) ;(timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
    }
    // write out another clock pulse with no data collection to set scaling to channel A, high gain
    digitalWrite (clockPin, HIGH) ;
    timeradd (&expectedTime, &delayTime, &expectedTime);
    gettimeofday (&actualTime, NULL);
    for ( ;(timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
    digitalWrite (clockPin, LOW) ;
    timeradd (&expectedTime, &delayTime, &expectedTime);
    for (gettimeofday (&actualTime, NULL) ;(timercmp (&actualTime, &expectedTime, <)); gettimeofday (&actualTime, NULL));
    // get values for each bit set from pre-computer array of powers of 2
    int result =0;
    for (int ibit =0; ibit < 24; ibit ++)
        result += dataArray [ibit] * pow2 [ibit];
    return result;
}

