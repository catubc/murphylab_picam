import ctypes
import numpy as np
import time as time
from concurrent.futures import ThreadPoolExecutor

_sum = ctypes.CDLL('/home/pi/murphylab_picam/temp/libsum.so')
_sum.c_function.argtypes = (ctypes.c_int, ctypes.POINTER(ctypes.c_int))

#Function to eventually strobe LEDs
def strobe(_sum):
    num_numbers = len(_sum.numbers)
    array_type = ctypes.c_int * num_numbers
    result = _sum.c_function(ctypes.c_int(num_numbers), array_type(*_sum.numbers))

#Initialize array of values
_sum.numbers = np.arange(5)

#Call on another thread
t = ThreadPoolExecutor(max_workers=1)
t.map(strobe, [_sum])
time.sleep(0.25)

#result = our_function(numbers)

for i in range(10):
    _sum.numbers[0] = np.random.randint(10) #-----------------> These changes are not detected in C
    print ("Python: ", _sum.numbers)
    time.sleep(.25)
