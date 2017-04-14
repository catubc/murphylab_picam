from ctypes import *
Foo = windll.mydll.Foo
Foo.argtypes = [POINTER(POINTER(c_ubyte)),POINTER(c_int)]
mem = POINTER(c_ubyte)()
size = c_int(0)
Foo(byref(mem),byref(size))
print (size.value,mem[0],mem[1],mem[2],mem[3])
