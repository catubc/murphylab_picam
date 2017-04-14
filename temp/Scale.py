from array import array
import HX711
"""HX711 is a c++ module from file HX711.cpython-34m.so that does the 
GPIO clocking and data reading from the HX711 load cell in c++ speed using
the wiringPi library.
The c++ approach was necessary as the Python GPIO code was not fast enough to be
reliable - the HX711 sleeps if the clock pin is held high for 60 ms, and
this would sometimes happen when running the GPIO with Python. """

class Scale:
    """
    Class to operate a scale based on an HX711 load cell amplifier
    """

    def __init__ (self,  dataPin, clockPin, gmPerUnit, initGPIO):
       """  
       Initializes a Python scale object, containing a pointer to a C++
       object that does threaded and non-threaded reading from HX711
       load cell amplifier
       :param dataPin:pin connected to the DAT pin on the HX711 breakout.
       :param ClockPin:pin connected to the SCK pin on the HX711 breakout
       :param gmPerUnit:scaling in grams/ 24-bit A/D unit
       initGPIO: set this only if GPIO has not been initialized yet
       """
       self.hx711ptr = HX711.new (dataPin, clockPin, gmPerUnit, initGPIO)
       self.threadArray = array ('f', (0 for i in range (0,100)))
       self.arraySize = 100
    
    def tare(self, nAvg, printVal):
        """
        Records the tare value, which will be subtracted from subsequent 
        scale reads. The tare value is stored in the C++ object
        :param nAvg:number of readings to average together to get tare
        :param printVal:if set, will print the tare value as well as save it
        :returns:the tare value, in A/D units, not scaled into grams
        """
        HX711.tare (self.hx711ptr, nAvg)
        if printVal == True:
            print ('Tare value is', self.getTareVal())

    def weigh (self, nAvg):
        """
        Gets an averaged weight value in grams with tare subtracted
        and scaling applied
        :param nAvg:the number of weight reading to average to get returned value
        :returns:weight in grams
        """
        return HX711.weigh (self.hx711ptr, nAvg)

    def weighOnce (self):
        """
        Gets weight from a single reading, in grams with tare and scaling applied
        :returns:weight in grams
        """
        return HX711.weigh (self.hx711ptr, 1)
    
    def readIntValue (self):
        """
        Reads the HX711 once and returns a signed integer value with neither tare nor 
        scaling applied.
        :returns:Raw value from 24 bit A/D, in signed integer format
        """
        return HX711.readIntValue ()

    def threadSetArraySize (self, newSize):
        """
        Resizes the array that is passed to the C++ module and is used for reading the scale
        rapidly from an independent thread
        :param newSize:number of elements in the array after resizing
        """
        self.threadArray = array ('f', (0 for i in range (0,newSize)))
        self.arraySize = newSize
        
    def threadStart (self, size):
        """
        Tells the C++ thread to start reading from the HX711 and placing results 
        in the array. When this function returns, the thread continues reading 
        until stopped or size weights have been obtained
        :param size:number of weights for the thread to place in the array. The array will be
        resized if needed
        """
        if size > self.arraySize:
            size = self.arraySize
        HX711.weighThreadStart(self.hx711ptr, self.threadArray, size)

    def threadStop (self):
        """
        Tells the C++ thread to stop reading weights and filling the array
        :returns:the number of weights the thread has placed in the array
        """
        return HX711.weighThreadStop (self.hx711ptr)

    def threadCheck (self):
        """
        Gets the number of weights the thread has already placed in the array, but
        does not twell the thread to stop reading weights and filling the array
        """
        return HX711.weighThreadCheck (self.hx711ptr)
            
    def setScaling (self, newScaling):
        """
        Sets scaling in grams/24-bit A/D units for the load cell amplifier to the passed-in
        value. The scaling is stored in the C++ object
        :param newScaling:the scaling, in grams/unit, to apply to load cell data
        """
        HX711.setScaling (self.hx711ptr, newScaling)

    def getScaling (self):
        """
        Gets the scaling in grams/24-bit A/D unit from the C++ object
        :returns:the scaling used for the load cell data in grams/24-bit A/D unit
        """
        return HX711.getScaling (self.hx711ptr)

    def getTareVal (self):
        """
        Gets the tare value in raw 24-bit A/D units from the C++ object
        :returns:tare value in raw 24-bit A/D units
        """
        return HX711.getTareValue (self.hx711ptr)

    def getClockPin (self):
        """
        Gets number of the GPIO pin to which the Pi exports the generated clock signal (SCK)
        :returns:GPIO pin number for clock signal
        """
        return HX711.getClockPin (self.hx711ptr)

    def getDataPin (self):
        """
        gets number of the GPIO pin from which the Pi reads the data (DAT)
        :return:number of the GPIO pin for data
        """
        return HX711.getDataPin (self.hx711ptr)

    def turnOn (self):
        """
        Makes sure the HX711 is ready to start weighing, waking it from the low power state if sleeping
        """
        HX711.turnOn (self.hx711ptr)

    def turnOff (self):
        """
        Puts the HX711 into a low power state
        """
        HX711.turnOff (self.hx711ptr)

"""
Main function that runs when not included from another module, used for
testing, calculating scaling, and simple weighing
"""
if __name__ == '__main__':
    DATAPIN = 23
    CLOCK = 24
    gmPerUnit = 7.152e-05
    nAvg = 10
    scale = Scale(DATAPIN, CLOCK, 7.152e-05, True)
    event = 0
    while event > -1:
        event = int (input ('Enter 0 to tare, 1 to weigh with avg, 2 to weigh once, 3 to turn OFF, 4 to turn ON, 5 for threaded read, -1 to quit:'))
        if event == -1:
            break
        elif event == 0:
            scale.tare(5,True)
        elif event ==1:
            print ('Weight =', scale.weigh(10), 'g')
        elif event == 2:
            print ('Weight =', scale.weighOnce(), 'g')
        elif event == 3:
            scale.turnOff()
        elif event == 4:
            scale.turnOn()
        elif event == 5:
            scale.threadStart (scale.arraySize)
            nReads = scale.threadCheck() 
            while nReads < scale.arraySize:
                print ("Thread has read ", nReads, " weights, last reading was ", scale.threadArray [nreads-1])
                nReads = scale.threadCheck()
