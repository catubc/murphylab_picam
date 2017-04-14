import ctypes



#Function to eventually strobe LEDs
def strobe(last_frame):
    _sum = ctypes.CDLL('/home/pi/murphylab_picam/strobe_c.so')
    _sum.strobe_c.argtype = (ctypes.POINTER(ctypes.c_int64))

    print ("...starting python strobing...")
    print ("...last frame: ", last_frame)
    print (type(last_frame))
    #_sum = ctypes.CDLL('./strobe_c.so')
    #_sum.strobe_c.argtypes = (ctypes.POINTER(ctypes.c_int64))

    #num_numbers = len(_sum.numbers)
    #array_type = ctypes.c_int * num_numbers
    #result = _sum.c_function(ctypes.c_int(num_numbers), array_type(*_sum.numbers))
    _sum.strobe_c(last_frame)
 
#strobe(64)
