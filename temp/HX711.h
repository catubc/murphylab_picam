#ifndef HX711_H
#define HX711_H
#include <stdio.h>
#include <pthread.h>
#include <wiringPi.h>
#include <sys/time.h>
#include <math.h>

/*   
    Class to get values from a HX711 Load Cell amplifier with scaling and taring
    Pin PD_SCK (clockPin) and DOUT (dataPin) are used for data retrieval, input selection, 
    gain selection and power down controls.
    When output data is not ready for retrieval, digital output pin DOUT is high.
    Serial clock input PD_SCK should be low. When DOUT goes to low, it indicates data is ready for retrieval.
    By applying 25~27 positive clock pulses at the PD_SCK pin, data is shifted out from the DOUT output pin.
    Each PD_SCK pulse shifts out one bit, starting with the MSB bit first, until all 24 bits are shifted out.
    The 25th pulse at PD_SCK input will pull DOUT pin back to high.
    Input and gain selection is controlled by adding a number of extra input PD_SCK pulses to the train
    after the data is collected

    PD_SCK Pulses   	Input channel   Gain
    25               		A              	128
    26               		B              	32
    27               		A              	64

    This code always runs the HX711 with high gain, input channel A, bu using 25 pulses
    
    Data is 24 bit two's-complement differential signal
    min value is -8388608, max value is 8388607
*/

// this C-style struct contains all the relevant thread variables and task variables, and is passed to the threaded weighing function
struct taskParams {
	int dataPin;
	int clockPin;
	float tareValue;
	float scaling;
        int * dataArray;
        int * pow2;
	volatile float * weightData; // pointer to the array to be filled with data, an array of floats
	volatile int getWeights; // calling function sets this to number of  weights  requested, or 0 to abort a series of weights
	volatile int gotWeights; // thread sets this to number of   weights  as they are obtained
	pthread_t taskThread;
	pthread_mutex_t taskMutex ;
	pthread_cond_t taskVar;	
};

class HX711{
	public:
	HX711 (int dp, int cp, float sp, bool ip);
	void tare (int nAvg, bool printVals);
        float weigh (int nAvg, bool printVals);
	void weighThreadStart (float * weights, int nWeights);
	int weighThreadStop (void);
	int weighThreadCheck (void);
	 int readValue (void);
        int getDataPin (void);
        int getClockPin(void);
        float getScaling (void);
        float getTareValue (void);
        void setScaling (float newScaling);
        void turnON(void);
        void turnOFF (void);

	private:
	int dataPin;
	int clockPin;
	float scaling;
        float tareValue;
        bool isPoweredUp;
        int dataArray [24];
        int pow2[24];
        struct timeval durTime;
        struct timeval delayTime;
        struct timeval actualTime;
        struct timeval expectedTime;
	// for threaded version
	struct taskParams theTask;
};

#endif // HX711_H
