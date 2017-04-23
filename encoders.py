# vim: set et sw=4 sts=4 fileencoding=utf-8:
#
# Python camera library for the Rasperry-Pi camera module
# Copyright (c) 2013-2015 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import (
    unicode_literals,
    print_function,
    division,
    absolute_import,
    )

# Make Py2's str and range equivalent to Py3's
str = type('')

#import datetime
#import threading
#import warnings
#import ctypes as ct

#from . import bcm_host, mmal, mmalobj as mo
#from .frames import PiVideoFrame, PiVideoFrameType
#from .exc import (
    #PiCameraMMALError,
    #PiCameraValueError,
    #PiCameraIOError,
    #PiCameraRuntimeError,
    #PiCameraResizerEncoding,
    #PiCameraAlphaStripping,
    #PiCameraResolutionRounded,
    #)


import io, os
import datetime
import threading
import warnings
import ctypes as ct

import numpy as np
import struct

#Additions by Cat
import matplotlib.pylab as plt
import curses
import time

from . import bcm_host, mmal, mmalobj as mo
from .frames import PiVideoFrame, PiVideoFrameType
from .streams import BufferIO
from .exc import (
    mmal_check,
    PiCameraError,
    PiCameraMMALError,
    PiCameraValueError,
    PiCameraRuntimeError,
    PiCameraResizerEncoding,
    PiCameraAlphaStripping,
    PiCameraResolutionRounded,
    )

class PiEncoder(object):
    """
    Base implementation of an MMAL encoder for use by PiCamera.

    The *parent* parameter specifies the :class:`PiCamera` instance that has
    constructed the encoder. The *camera_port* parameter provides the MMAL
    camera port that the encoder should enable for capture (this will be the
    still or video port of the camera component). The *input_port* parameter
    specifies the MMAL port that the encoder should connect to its input.
    Sometimes this will be the same as the camera port, but if other components
    are present in the pipeline (e.g. a splitter), it may be different.

    The *format* parameter specifies the format that the encoder should
    produce in its output. This is specified as a string and will be one of
    the following for image encoders:

    * ``'jpeg'``
    * ``'png'``
    * ``'gif'``
    * ``'bmp'``
    * ``'yuv'``
    * ``'rgb'``
    * ``'rgba'``
    * ``'bgr'``
    * ``'bgra'``

    And one of the following for video encoders:

    * ``'h264'``
    * ``'mjpeg'``

    The *resize* parameter is either ``None`` (indicating no resizing
    should take place), or a ``(width, height)`` tuple specifying the
    resolution that the output of the encoder should be resized to.

    Finally, the *options* parameter specifies additional keyword arguments
    that can be used to configure the encoder (e.g. bitrate for videos, or
    quality for images).

    .. attribute:: camera_port

        The :class:`~mmalobj.MMALVideoPort` that needs to be activated and
        deactivated in order to start/stop capture. This is not necessarily the
        port that the encoder component's input port is connected to (for
        example, in the case of video-port based captures, this will be the
        camera video port behind the splitter).

    .. attribute:: encoder

        The :class:`~mmalobj.MMALComponent` representing the encoder, or
        ``None`` if no encoder component has been created (some encoder classes
        don't use an actual encoder component, for example
        :class:`PiRawImageMixin`).

    .. attribute:: event

        A :class:`threading.Event` instance used to synchronize operations
        (like start, stop, and split) between the control thread and the
        callback thread.

    .. attribute:: exception

        If an exception occurs during the encoder callback, this attribute is
        used to store the exception until it can be re-raised in the control
        thread.

    .. attribute:: format

        The image or video format that the encoder is expected to produce. This
        is equal to the value of the *format* parameter.

    .. attribute:: input_port

        The :class:`~mmalobj.MMALVideoPort` that the encoder should be
        connected to.

    .. attribute:: output_port

        The :class:`~mmalobj.MMALVideoPort` that produces the encoder's output.
        In the case no encoder component is created, this should be the
        camera/component output port responsible for producing data. In other
        words, this attribute **must** be set on initialization.

    .. attribute:: outputs

        A mapping of ``key`` to ``(output, opened)`` tuples where ``output``
        is a file-like object, and ``opened`` is a bool indicating whether or
        not we opened the output object (and thus whether we are responsible
        for eventually closing it).

    .. attribute:: outputs_lock

        A :func:`threading.Lock` instance used to protect access to
        :attr:`outputs`.

    .. attribute:: parent

        The :class:`PiCamera` instance that created this PiEncoder instance.

    .. attribute:: pool

        A pointer to a pool of MMAL buffers.

    .. attribute:: resizer

        The :class:`~mmalobj.MMALResizer` component, or ``None`` if no resizer
        component has been created.
    """

    DEBUG = 0
    encoder_type = None

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        self.parent = parent
        self.encoder = None
        self.resizer = None
        self.camera_port = camera_port
        self.input_port = input_port
        self.output_port = None
        self.outputs_lock = threading.Lock() # protects access to self.outputs
        self.outputs = {}
        self.exception = None
        self.event = threading.Event()
        try:
            if parent and parent.closed:
                raise PiCameraRuntimeError("Camera is closed")
            if resize:
                self._create_resizer(*mo.to_resolution(resize))
            self._create_encoder(format, **options)
            if self.encoder:
                self.encoder.connection.enable()
            if self.resizer:
                self.resizer.connection.enable()
        except:
            self.close()
            raise

    def _create_resizer(self, width, height):
        """
        Creates and configures an :class:`~mmalobj.MMALResizer` component.

        This is called when the initializer's *resize* parameter is something
        other than ``None``. The *width* and *height* parameters are passed to
        the constructed resizer. Note that this method only constructs the
        resizer - it does not connect it to the encoder. The method sets the
        :attr:`resizer` attribute to the constructed resizer component.
        """
        self.resizer = mo.MMALResizer()
        self.resizer.inputs[0].connect(self.input_port)
        self.resizer.outputs[0].copy_from(self.resizer.inputs[0])
        self.resizer.outputs[0].format = mmal.MMAL_ENCODING_I420
        self.resizer.outputs[0].framesize = (width, height)
        self.resizer.outputs[0].commit()

    def _create_encoder(self, format):
        """
        Creates and configures the :class:`~mmalobj.MMALEncoder` component.

        This method only constructs the encoder; it does not connect it to the
        input port. The method sets the :attr:`encoder` attribute to the
        constructed encoder component, and the :attr:`output_port` attribute to
        the encoder's output port (or the previously constructed resizer's
        output port if one has been requested). Descendent classes extend this
        method to finalize encoder configuration.

        .. note::

            It should be noted that this method is called with the
            initializer's ``option`` keyword arguments. This base
            implementation expects no additional arguments, but descendent
            classes extend the parameter list to include options relevant to
            them.
        """
        assert not self.encoder
        self.encoder = self.encoder_type()
        self.output_port = self.encoder.outputs[0]
        if self.resizer:
            self.encoder.inputs[0].connect(self.resizer.outputs[0])
        else:
            self.encoder.inputs[0].connect(self.input_port)
        self.encoder.outputs[0].copy_from(self.encoder.inputs[0])
        # NOTE: We deliberately don't commit the output port format here as
        # this is a base class and the output configuration is incomplete at
        # this point. Descendents are expected to finish configuring the
        # encoder and then commit the port format themselves

    def _callback(self, port, buf):
        """
        The encoder's main callback function.

        When the encoder is active, this method is periodically called in a
        background thread. The *port* parameter specifies the :class:`MMALPort`
        providing the output (typically this is the encoder's output port, but
        in the case of unencoded captures may simply be a camera port), while
        the *buf* parameter is an :class:`~mmalobj.MMALBuffer` which can be
        used to obtain the data to write, along with meta-data about the
        current frame.

        This method must set :attr:`event` when the encoder has finished (and
        should set :attr:`exception` if an exception occurred during encoding).

        Developers wishing to write a custom encoder class may find it simpler
        to override the :meth:`_callback_write` method, rather than deal with
        these complexities.
        """
        if self.DEBUG > 1:
            print(repr(buf))
        try:
            stop = self._callback_write(buf)
        except Exception as e:
            stop = True
            self.exception = e
        if stop:
            self.event.set()
        return stop

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
       
        """
        Writes output on behalf of the encoder callback function.

        This method is called by :meth:`_callback` to handle writing to an
        object in :attr:`outputs` identified by *key*. The *buf* parameter is
        an :class:`~mmalobj.MMALBuffer` which can be used to obtain the data.
        The method is expected to return a boolean to indicate whether output
        is complete (``True``) or whether more data is expected (``False``).

        The default implementation simply writes the contents of the buffer to
        the output identified by *key*, and returns ``True`` if the buffer
        flags indicate end of stream. Image encoders will typically override
        the return value to indicate ``True`` on end of frame (as they only
        wish to output a single image). Video encoders will typically override
        this method to determine where key-frames and SPS headers occur.
        """
        if buf.length:
            with self.outputs_lock:
                try:
                    output = self.outputs[key][0]
                    self.output_times.append(self.frame.timestamp)      #Save time stamps for each frame in list
                    self.gpu_last_frame[0]= self.frame.timestamp        #Save time stamp in ctype for C access; DONOT CHANGE !!
                    
                    #PARALLEL SAVE IN C --------- should eventually be default mode if it works; ONE LESS CONDITIONAL
                    if self.write_mode == 0:                    #Write do disk directly
                        stack_index = int(self.frame_ctr[0]/self.save_block[0])%2 #this can be 0 or 1
                        if (stack_index==0): 
                            self.image_stack_0[self.frame_ctr[0]%self.save_block[0]].value=buf.data
                        else:
                            self.image_stack_1[self.frame_ctr[0]%self.save_block[0]].value=buf.data

                        written = buf.length
                        
                        #TEMPORARILY save to disk FOR DEBUGGING
                        #written = output.write(buf.data)
                        
                        #self.written_array.append(buf.data)
                        
                        self.frame_ctr[0]=self.frame_ctr[0]+1   #This value is dynamically tracked in C; carefulwhere placed

                        #    written = buf.length
                    #SAVE TO DISK DIRECTLY
                    elif self.write_mode == 1:                    #Write do disk directly
                        written = output.write(buf.data)
                        
                    #SAVE TO MEMORY ONLY
                    elif self.write_mode == 2:                  #Write to memory only
                        self.written_array.append(buf.data)
                        written = buf.length
                    
                    #ITENSITY CHECKING CODE ************* THIS NEEDS TO BE MOVED FROM HERE *******************
                    elif self.write_mode == 3:
                        
                        #TEXT BASED GRAPHICS; screen is 62 x 158 in xserver; 64 x 160 command line
                        data_array = struct.unpack(self.n_pixels_string, buf.data)		#MIGHT WANT TO UNPACK JUST SOME OF THE DATA!!!
                        #red_line = struct.unpack(str(int(self.n_pixels))+"B", 
                        #            buf.data[::3][int(self.n_pixels**2/2):int(self.n_pixels**2/2+self.n_pixels)])		
                        
                        red_line = np.mean(np.array(data_array[::3]).reshape(self.n_pixels,self.n_pixels),axis=0)
                        green_line = np.mean(np.array(data_array[1::3]).reshape(self.n_pixels,self.n_pixels),axis=0)
                        blue_line = np.mean(np.array(data_array[2::3]).reshape(self.n_pixels,self.n_pixels),axis=0)
                        

                        #green_line = struct.unpack(str(int(self.n_pixels))+"B", 
                        #            buf.data[1::3][int(self.n_pixels**2/2):int(self.n_pixels**2/2+self.n_pixels)])		
                        #blue_line = struct.unpack(str(int(self.n_pixels))+"B", 
                        #            buf.data[2::3][int(self.n_pixels**2/2):int(self.n_pixels**2/2+self.n_pixels)])		

                        #Horizonal display
                        line_0 = np.int32(red_line)*0
                        line_100 = np.int32(red_line)*0+100
                        line_200 = np.int32(red_line)*0+200
                        line_255 = np.int32(red_line)*0+255
                        
                        sub_sample_y = 255./self.curses_size_y
                        sub_sample_x = float(self.n_pixels-1)/self.curses_size_x
                        sub_sample_list = np.int32(np.linspace(0,self.n_pixels-1,self.curses_size_x))

                        #Print all horizontal curves
                        for k in sub_sample_list: 
                            #Red color
                            self.curses_window.addstr(self.curses_size_y-int(red_line[k]/sub_sample_y)-2, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(2))
                            self.curses_window.addstr(self.curses_size_y-int(green_line[k]/sub_sample_y)-2, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(3))
                            self.curses_window.addstr(self.curses_size_y-int(blue_line[k]/sub_sample_y)-2, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(5))

                            self.curses_window.addstr(self.curses_size_y-int(line_0[k]/sub_sample_y)-1, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(0))
                            self.curses_window.addstr(self.curses_size_y-int(line_100[k]/sub_sample_y)-1, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(0))
                            self.curses_window.addstr(self.curses_size_y-int(line_200[k]/sub_sample_y)-1, 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(0))
                            #self.curses_window.addstr(np.max(0,self.curses_size_y-int(line_255[k]/sub_sample_y)-1), 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(0))
                            self.curses_window.addstr(self.curses_size_y-int(line_255[k]/sub_sample_y), 1+int(k/sub_sample_x/1.05), "*", curses.color_pair(0))

                        #Print vertical lines
                        for k in range(0,self.curses_size_y,1):
                            self.curses_window.addstr(k, 0, "*", curses.color_pair(0))
                            self.curses_window.addstr(k, int(self.curses_size_x/2.-2), "*", curses.color_pair(0))
                            self.curses_window.addstr(k, self.curses_size_x-5, "*", curses.color_pair(0))

                        self.curses_window.addstr(self.curses_size_y-2, self.curses_size_x-2, "0", curses.color_pair(0))
                        self.curses_window.addstr(0, self.curses_size_x-3 , "255", curses.color_pair(0))

                        self.curses_window.addstr(self.curses_size_y-int(100./sub_sample_y)-1, self.curses_size_x-3, "100", curses.color_pair(0))
                        self.curses_window.addstr(self.curses_size_y-int(200./sub_sample_y)-1, self.curses_size_x-3, "200", curses.color_pair(0))

                        #self.curses_window.getch()
                        self.curses_window.refresh()
                        #time.sleep(.25)
                        self.curses_window.clear()
                        
                        written = buf.length
                        self.write_counter+=1

                        
                except KeyError:
                    # No output associated with the key type; discard the
                    # data
                    pass
                else:
                    # Ignore None return value; most Python 2 streams have
                    # no return value for write()
                    if (written is not None) and (written != buf.length):
                        raise PiCameraError(
                            "Failed to write %d bytes from buffer to "
                            "output %r" % (buf.length, output))
        return bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_EOS)

    #Cat function to start strobing lights
    def strobe(self):
        ''' Strobe code. First, call python code on separate thread to initalize C code for strobing.
            Second, call strobe code in C, passing pointer to last_frame values.
        '''
        _sum = ct.CDLL('/home/pi/murphylab_picam/strobe_c.so')
        _sum.strobe_c.argtype = (ct.POINTER(ct.c_uint64), ct.POINTER(ct.c_uint32))
        _sum.strobe_c(self.gpu_last_frame, self.save_led_state)
    
    def c_saving(self):
        ''' Code to save data to disk in parallel to ongoing acquisition
        '''
        _sum = ct.CDLL('/home/pi/murphylab_picam/save_c.so')
        _sum.save_c.argtype = (ct.POINTER(ct.c_int32), ct.POINTER(ct.c_int32), ct.POINTER(ct.c_char), ct.POINTER(ct.c_char))
        _sum.save_c(self.save_block, self.frame_ctr, self.image_stack_0, self.image_stack_1)
        
    
    def _open_output(self, output, key=PiVideoFrameType.frame):
        """
        Opens *output* and associates it with *key* in :attr:`outputs`.

        If *output* is a string, this method opens it as a filename and keeps
        track of the fact that the encoder was the one to open it (which
        implies that :meth:`_close_output` should eventually close it).
        Otherwise, if *output* has a ``write`` method it is assumed to be a
        file-like object and it is used verbatim. If *output* is neither a
        string, nor an object with a ``write`` method it is assumed to be a
        writeable object supporting the buffer protocol (this is wrapped in
        a :class:`BufferIO` stream to simplify writing).

        The opened output is added to the :attr:`outputs` dictionary with the
        specified *key*.
        """
        with self.outputs_lock:
            opened = isinstance(output, (bytes, str))
            if opened:
                # Open files in binary mode with a decent buffer size
                self.output_file_name = output
                self.written_array = [] #np.zeros((9100, 128*128*3), dtype=np.uint8)
                self.output_times = []
                self.first_100_frames=[]
                #self.output_times = open(output + '_time.txt', 'wt')
                self.write_counter = 0
                self.write_mode = np.loadtxt(output[:-4]+'_rec_mode.txt')

                #INITIALIZE last frame variable; start parallel process;
                #Declare using ctypes: e.g. _sum.numbers = (ctypes.c_int * 5)(*range(5))


                ''' PARALLEL STROBING CODE
                    INITIALIZE frame variable to be share with C; NB: Must use array and insert val into index=0; 
                    #otherwise the entire variable object is destroyed every frame time assignment
                '''
                self.gpu_last_frame = (ct.c_uint64*2)(*range(2))    #Init variable
                self.save_led_state = (ct.c_uint32*2)(*range(2))    #Init variable
                if self.write_mode == 3: 
                    self.save_led_state[0]=0    #DO NOT SAVE LED TIMES DURING INTENSITY CHECK
                else:
                    self.save_led_state[0]=1    #SAVE LED TIMES AFTER DATA LOADED
                if True:
                    t = threading.Thread(target=self.strobe)            #start python+C code on 2nd thread
                    t.start()
    
                #Load number of pixels from disk:
                self.n_pixels = np.loadtxt(output[:-4]+"_n_pixels.txt")
                self.n_pixels_string = str(int(self.n_pixels)**2*3)+"B"      #Need this for intensity check above to convert byte to data
                
                #Open a file to write lastest frame; do not close it;
                #self.latest_frame_file = open(self.output_file_name + '_latest_frame.txt', 'w') 
                #self.latest_frame_file.write('%d' % self.frame.timestamp)
                
                #Load mode from disk; couldn't figure out how to pass attribute to encoder object
                if self.write_mode == 3:
                    #import matplotlib.rcsetup as rcsetup
                    #print (rcsetup.all_backends)
                    #plt.ion()

                    self.curses_window = curses.initscr()
                    self.curses_size_y, self.curses_size_x = self.curses_window.getmaxyx()
                    print (self.curses_size_y, self.curses_size_x)
                    curses.start_color()
                    curses.use_default_colors()
                    for i in range(0, curses.COLORS,1):
                        curses.init_pair(i+1, i, -1)
                            
                ''' PARALLEL C SAVE CODE. 
                    Requires initalization of 2 arrays;
                '''
                if self.write_mode == 0:
                    self.save_block = (ct.c_int32*2)()
                    self.save_block[0] = 1000
                    self.frame_ctr = (ct.c_int32*2)()
                    self.frame_ctr.value = 0           #Starting value of counter; need to index on entry to loop above
                    #self.frame_ctr[1] = 0              #value = -2 is set on exit to as flag to C code
                    #self.frame_ctr=0
                    #print (type(self.frame_ctr))
                    #self.image_stack = (((ct.c_uint8*2)*100)*(int(self.n_pixels)**2*3))()   #Init 2 x 100 x size of each stack
                    #self.image_stack = (((ct.c_byte*(int(self.n_pixels)**2*3))*100)*2)()   #Init 2 x 100 x size of each stack
                    self.image_stack_0 = ((ct.c_char*(int(self.n_pixels)**2*3))*self.save_block[0])()   #Init 2 x 100 x size of each stack
                    self.image_stack_1 = ((ct.c_char*(int(self.n_pixels)**2*3))*self.save_block[0])()   #Init 2 x 100 x size of each stack
                    #self.image_stack[0][99][0]=0
                    #self.image_stack[1][99][0]=0
                    t = threading.Thread(target=self.c_saving)            #start python+C code on 2nd thread
                    t.start()
                
                #print ("... write_mode: ", self.write_mode)                
                output = io.open(output, 'wb', buffering=0) #65536
            else:
                try:
                    output.write
                    #self.output_times.write
                except AttributeError:
                    # If there's no write method, try and treat the output as
                    # a writeable buffer
                    opened = True
                    output = BufferIO(output)
            self.outputs[key] = (output, opened)

    def _close_output(self, key=PiVideoFrameType.frame):
        """
        Closes the output associated with *key* in :attr:`outputs`.

        Closes the output object associated with the specified *key*, and
        removes it from the :attr:`outputs` dictionary (if we didn't open the
        object then we attempt to flush it instead).
        """
        #Close matplotlib figs
        #plt.close()
        curses.endwin()
        if self.write_mode==0:
            self.frame_ctr[1]=1       #Save this flag for C code to indicate termination; necessary because otherwise C will loop indefinitely
                                    #might be doable another way
        
        file_out = open(self.output_file_name + '_time.txt', 'wt')
        for time in self.output_times: file_out.write(str(time)+'\n') #self.camera.
        file_out.close()

        if self.write_mode==2:
            print ("...saving to disk from memory...")
            output = open(self.output_file_name, 'wb') #65536
            for frame in self.written_array: output.write(frame)
            output.close()
 
        with self.outputs_lock:
            try:
                (output, opened) = self.outputs.pop(key)
            except KeyError:
                pass
            else:
                if opened:
                    output.close()
                else:
                    try:
                        output.flush()
                    except AttributeError:
                        pass


    @property
    def active(self):
        """
        Returns ``True`` if the MMAL encoder exists and is enabled.
        """
        try:
            return bool(self.output_port.enabled)
        except AttributeError:
            # output_port can be None; avoid a (demonstrated) race condition
            # by catching AttributeError
            return False

    def start(self, output):
        """
        Starts the encoder object writing to the specified output.

        This method is called by the camera to start the encoder capturing
        data from the camera to the specified output. The *output* parameter
        is either a filename, or a file-like object (for image and video
        encoders), or an iterable of filenames or file-like objects (for
        multi-image encoders).
        """
        self.event.clear()
        self.exception = None
        self._open_output(output)
        with self.parent._encoders_lock:
            self.output_port.enable(self._callback)
            if self.DEBUG > 0:
                mo.print_pipeline(self.output_port)
            self.parent._start_capture(self.camera_port)

    def wait(self, timeout=None):
        """
        Waits for the encoder to finish (successfully or otherwise).

        This method is called by the owning camera object to block execution
        until the encoder has completed its task. If the *timeout* parameter
        is None, the method will block indefinitely. Otherwise, the *timeout*
        parameter specifies the (potentially fractional) number of seconds
        to block for. If the encoder finishes successfully within the timeout,
        the method returns ``True``. Otherwise, it returns ``False``.
        """
        result = self.event.wait(timeout)
        if result:
            self.stop()
            # Check whether the callback set an exception
            if self.exception:
                raise self.exception
        return result

    def stop(self):
        """
        Stops the encoder, regardless of whether it's finished.

        This method is called by the camera to terminate the execution of the
        encoder. Typically, this is used with video to stop the recording, but
        can potentially be called in the middle of image capture to terminate
        the capture.
        """
        # NOTE: The active test below is necessary to prevent attempting to
        # re-enter the parent lock in the case the encoder is being torn down
        # by an error in the constructor
        if self.active:
            if self.parent and self.camera_port:
                with self.parent._encoders_lock:
                    self.parent._stop_capture(self.camera_port)
            self.output_port.disable()
        self.event.set()
        self._close_output()

    def close(self):
        """
        Finalizes the encoder and deallocates all structures.

        This method is called by the camera prior to destroying the encoder (or
        more precisely, letting it go out of scope to permit the garbage
        collector to destroy it at some future time). The method destroys all
        components that the various create methods constructed and resets their
        attributes.
        """
        self.stop()
        if self.encoder:
            self.encoder.disconnect()
        if self.resizer:
            self.resizer.disconnect()
        if self.encoder:
            self.encoder.close()
            self.encoder = None
        if self.resizer:
            self.resizer.close()
            self.resizer = None
        self.output_port = None


class MMALBufferAlphaStrip(mo.MMALBuffer):
    """
    An MMALBuffer descendent that strips alpha bytes from the buffer data. This
    is used internally by PiRawMixin when it needs to strip alpha bytes itself
    (e.g. because an appropriate format cannot be selected on an output port).
    """

    def __init__(self, buf):
        super(MMALBufferAlphaStrip, self).__init__(buf)
        self._stripped = bytearray(super(MMALBufferAlphaStrip, self).data)
        del self._stripped[3::4]

    @property
    def length(self):
        return len(self._stripped)

    @property
    def data(self):
        return self._stripped


class PiRawMixin(PiEncoder):
    """
    Mixin class for "raw" (unencoded) output.

    This mixin class overrides the initializer of :class:`PiEncoder`, along
    with :meth:`_create_resizer` and :meth:`_create_encoder` to configure the
    pipeline for unencoded output. Specifically, it disables the construction
    of an encoder, and sets the output port to the input port passed to the
    initializer, unless resizing is required (either for actual resizing, or
    for format conversion) in which case the resizer's output is used.
    """

    RAW_ENCODINGS = {
        # name   mmal-encoding             bytes-per-pixel
        'yuv':  (mmal.MMAL_ENCODING_I420,  1.5),
        'rgb':  (mmal.MMAL_ENCODING_RGB24, 3),
        'rgba': (mmal.MMAL_ENCODING_RGBA,  4),
        'bgr':  (mmal.MMAL_ENCODING_BGR24, 3),
        'bgra': (mmal.MMAL_ENCODING_BGRA,  4),
        }

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        encoding, bpp = self.RAW_ENCODINGS[format]
        # Workaround: on older firmwares, non-YUV encodings aren't supported on
        # the still port. If a non-YUV format is requested without resizing,
        # test whether we can commit the requested format on the input port and
        # if this fails, set resize to force resizer usage
        if resize is None and encoding != mmal.MMAL_ENCODING_I420:
            input_port.format = encoding
            try:
                input_port.commit()
            except PiCameraMMALError as e:
                if e.status != mmal.MMAL_EINVAL:
                    raise
                resize = input_port.framesize
                warnings.warn(
                    PiCameraResizerEncoding(
                        "using a resizer to perform non-YUV encoding; "
                        "upgrading your firmware with sudo rpi-update "
                        "may improve performance"))
        # Workaround: If a non-alpha format is requested with the resizer, use
        # the alpha-inclusive format and set a flag to get the callback to
        # strip the alpha bytes
        self._strip_alpha = False
        if resize:
            width, height = resize
            try:
                format = {
                    'rgb': 'rgba',
                    'bgr': 'bgra',
                    }[format]
                self._strip_alpha = True
                warnings.warn(
                    PiCameraAlphaStripping(
                        "using alpha-stripping to convert to non-alpha "
                        "format; you may find the equivalent alpha format "
                        "faster"))
            except KeyError:
                pass
        else:
            width, height = input_port.framesize
        # Workaround (#83): when the resizer is used the width must be aligned
        # (both the frame and crop values) to avoid an error when the output
        # port format is set (height is aligned too, simply for consistency
        # with old picamera versions). Warn the user as they're not going to
        # get the resolution they expect
        if not resize and format != 'yuv' and input_port.name.startswith('vc.ril.video_splitter'):
            # Workaround: Expected frame size is rounded to 16x16 when splitter
            # port with no resizer is used and format is not YUV
            fwidth = bcm_host.VCOS_ALIGN_UP(width, 16)
        else:
            fwidth = bcm_host.VCOS_ALIGN_UP(width, 32)
        fheight = bcm_host.VCOS_ALIGN_UP(height, 16)
        if fwidth != width or fheight != height:
            warnings.warn(
                PiCameraResolutionRounded(
                    "frame size rounded up from %dx%d to %dx%d" % (
                        width, height, fwidth, fheight)))
        if resize:
            resize = (fwidth, fheight)
        # Workaround: Calculate the expected frame size, to be used by the
        # callback to decide when a frame ends. This is to work around a
        # firmware bug that causes the raw image to be returned twice when the
        # maximum camera resolution is requested
        self._frame_size = int(fwidth * fheight * bpp)
        super(PiRawMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)

    def _create_encoder(self, format):
        """
        Overridden to skip creating an encoder. Instead, this class simply uses
        the resizer's port as the output port (if a resizer has been
        configured) or the specified input port otherwise.
        """
        if self.resizer:
            self.output_port = self.resizer.outputs[0]
        else:
            self.output_port = self.input_port
        try:
            self.output_port.format = self.RAW_ENCODINGS[format][0]
        except KeyError:
            raise PiCameraValueError('unknown format %s' % format)
        self.output_port.commit()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        _callback_write(buf, key=PiVideoFrameType.frame)

        Overridden to strip alpha bytes when required.
        """
        if self._strip_alpha:
            return super(PiRawMixin, self)._callback_write(MMALBufferAlphaStrip(buf._buf), key)
        else:
            return super(PiRawMixin, self)._callback_write(buf, key)


class PiVideoEncoder(PiEncoder):
    """
    Encoder for video recording.

    This derivative of :class:`PiEncoder` configures itself for H.264 or MJPEG
    encoding.  It also introduces a :meth:`split` method which is used by
    :meth:`~PiCamera.split_recording` and :meth:`~PiCamera.record_sequence` to
    redirect future output to a new filename or object. Finally, it also
    extends :meth:`PiEncoder.start` and :meth:`PiEncoder._callback_write` to
    track video frame meta-data, and to permit recording motion data to a
    separate output object.
    """

    encoder_type = mo.MMALVideoEncoder

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiVideoEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._next_output = []
        self.frame = None

    def _create_encoder(
            self, format, bitrate=17000000, intra_period=None, profile='high',
            level='4', quantization=0, quality=0, inline_headers=True,
            sei=False, sps_timing=False, motion_output=None,
            intra_refresh=None):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the video encoder for H.264 or MJPEG output.
        """
        super(PiVideoEncoder, self)._create_encoder(format)

        # XXX Remove quantization in 2.0
        quality = quality or quantization

        try:
            self.output_port.format = {
                'h264':  mmal.MMAL_ENCODING_H264,
                'mjpeg': mmal.MMAL_ENCODING_MJPEG,
                }[format]
        except KeyError:
            raise PiCameraValueError('Unsupported format %s' % format)

        if format == 'h264':
            try:
                profile = {
                    'baseline':    mmal.MMAL_VIDEO_PROFILE_H264_BASELINE,
                    'main':        mmal.MMAL_VIDEO_PROFILE_H264_MAIN,
                    'extended':    mmal.MMAL_VIDEO_PROFILE_H264_EXTENDED,
                    'high':        mmal.MMAL_VIDEO_PROFILE_H264_HIGH,
                    'constrained': mmal.MMAL_VIDEO_PROFILE_H264_CONSTRAINED_BASELINE,
                    }[profile]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 profile %s" % profile)
            try:
                level = {
                    '1':   mmal.MMAL_VIDEO_LEVEL_H264_1,
                    '1.0': mmal.MMAL_VIDEO_LEVEL_H264_1,
                    '1b':  mmal.MMAL_VIDEO_LEVEL_H264_1b,
                    '1.1': mmal.MMAL_VIDEO_LEVEL_H264_11,
                    '1.2': mmal.MMAL_VIDEO_LEVEL_H264_12,
                    '1.3': mmal.MMAL_VIDEO_LEVEL_H264_13,
                    '2':   mmal.MMAL_VIDEO_LEVEL_H264_2,
                    '2.0': mmal.MMAL_VIDEO_LEVEL_H264_2,
                    '2.1': mmal.MMAL_VIDEO_LEVEL_H264_21,
                    '2.2': mmal.MMAL_VIDEO_LEVEL_H264_22,
                    '3':   mmal.MMAL_VIDEO_LEVEL_H264_3,
                    '3.0': mmal.MMAL_VIDEO_LEVEL_H264_3,
                    '3.1': mmal.MMAL_VIDEO_LEVEL_H264_31,
                    '3.2': mmal.MMAL_VIDEO_LEVEL_H264_32,
                    '4':   mmal.MMAL_VIDEO_LEVEL_H264_4,
                    '4.0': mmal.MMAL_VIDEO_LEVEL_H264_4,
                    '4.1': mmal.MMAL_VIDEO_LEVEL_H264_41,
                    '4.2': mmal.MMAL_VIDEO_LEVEL_H264_42,
                    }[level]
            except KeyError:
                raise PiCameraValueError("Invalid H.264 level %s" % level)

            # From https://en.wikipedia.org/wiki/H.264/MPEG-4_AVC#Levels
            bitrate_limit = {
                # level, high-profile:  bitrate
                (mmal.MMAL_VIDEO_LEVEL_H264_1,  False): 64000,
                (mmal.MMAL_VIDEO_LEVEL_H264_1b, False): 128000,
                (mmal.MMAL_VIDEO_LEVEL_H264_11, False): 192000,
                (mmal.MMAL_VIDEO_LEVEL_H264_12, False): 384000,
                (mmal.MMAL_VIDEO_LEVEL_H264_13, False): 768000,
                (mmal.MMAL_VIDEO_LEVEL_H264_2,  False): 2000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_21, False): 4000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_22, False): 4000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_3,  False): 10000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_31, False): 14000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_32, False): 20000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_4,  False): 20000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_41, False): 50000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_42, False): 50000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_1,  True):  80000,
                (mmal.MMAL_VIDEO_LEVEL_H264_1b, True):  160000,
                (mmal.MMAL_VIDEO_LEVEL_H264_11, True):  240000,
                (mmal.MMAL_VIDEO_LEVEL_H264_12, True):  480000,
                (mmal.MMAL_VIDEO_LEVEL_H264_13, True):  960000,
                (mmal.MMAL_VIDEO_LEVEL_H264_2,  True):  2500000,
                (mmal.MMAL_VIDEO_LEVEL_H264_21, True):  5000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_22, True):  5000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_3,  True):  12500000,
                (mmal.MMAL_VIDEO_LEVEL_H264_31, True):  17500000,
                (mmal.MMAL_VIDEO_LEVEL_H264_32, True):  25000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_4,  True):  25000000,
                (mmal.MMAL_VIDEO_LEVEL_H264_41, True):  62500000,
                (mmal.MMAL_VIDEO_LEVEL_H264_42, True):  62500000,
                }[level, profile == mmal.MMAL_VIDEO_PROFILE_H264_HIGH]
            if bitrate > bitrate_limit:
                raise PiCameraValueError(
                    'bitrate %d exceeds %d which is the limit for the '
                    'selected H.264 level and profile' %
                    (bitrate, bitrate_limit))
            self.output_port.bitrate = bitrate
            self.output_port.commit()

            # Again, from https://en.wikipedia.org/wiki/H.264/MPEG-4_AVC#Levels
            macroblocks_per_s_limit, macroblocks_limit = {
                #level: macroblocks/s, macroblocks
                mmal.MMAL_VIDEO_LEVEL_H264_1:  (1485,   99),
                mmal.MMAL_VIDEO_LEVEL_H264_1b: (1485,   99),
                mmal.MMAL_VIDEO_LEVEL_H264_11: (3000,   396),
                mmal.MMAL_VIDEO_LEVEL_H264_12: (6000,   396),
                mmal.MMAL_VIDEO_LEVEL_H264_13: (11880,  396),
                mmal.MMAL_VIDEO_LEVEL_H264_2:  (11880,  396),
                mmal.MMAL_VIDEO_LEVEL_H264_21: (19800,  792),
                mmal.MMAL_VIDEO_LEVEL_H264_22: (20250,  1620),
                mmal.MMAL_VIDEO_LEVEL_H264_3:  (40500,  1620),
                mmal.MMAL_VIDEO_LEVEL_H264_31: (108000, 3600),
                mmal.MMAL_VIDEO_LEVEL_H264_32: (216000, 5120),
                mmal.MMAL_VIDEO_LEVEL_H264_4:  (245760, 8192),
                mmal.MMAL_VIDEO_LEVEL_H264_41: (245760, 8192),
                mmal.MMAL_VIDEO_LEVEL_H264_42: (522240, 8704),
                }[level]
            w, h = self.output_port.framesize
            w = bcm_host.VCOS_ALIGN_UP(w, 16) >> 4
            h = bcm_host.VCOS_ALIGN_UP(h, 16) >> 4
            if w * h > macroblocks_limit:
                raise PiCameraValueError(
                    'output resolution %s exceeds macroblock limit (%d) for '
                    'the selected H.264 profile and level' %
                    (self.output_port.framesize, macroblocks_limit))
            if self.parent:
                framerate = self.parent.framerate + self.parent.framerate_delta
            else:
                framerate = self.input_port.framerate
            if w * h * framerate > macroblocks_per_s_limit:
                raise PiCameraValueError(
                    'output resolution and framerate exceeds macroblocks/s '
                    'limit (%d) for the selected H.264 profile and '
                    'level' % macroblocks_per_s_limit)

            mp = mmal.MMAL_PARAMETER_VIDEO_PROFILE_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_PROFILE,
                        ct.sizeof(mmal.MMAL_PARAMETER_VIDEO_PROFILE_T),
                        ),
                    )
            mp.profile[0].profile = profile
            mp.profile[0].level = level
            self.output_port.params[mmal.MMAL_PARAMETER_PROFILE] = mp

            if inline_headers:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_HEADER] = True
            if sei:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_SEI_ENABLE] = True
            if sps_timing:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_SPS_TIMING] = True
            if motion_output is not None:
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INLINE_VECTORS] = True

            # We need the intra-period to calculate the SPS header timeout in
            # the split method below. If one is not set explicitly, query the
            # encoder's default
            if intra_period is not None:
                self.output_port.params[mmal.MMAL_PARAMETER_INTRAPERIOD] = intra_period
                self._intra_period = intra_period
            else:
                self._intra_period = self.output_port.params[mmal.MMAL_PARAMETER_INTRAPERIOD]

            if intra_refresh is not None:
                # Get the intra-refresh structure first as there are several
                # other fields in it which we don't wish to overwrite
                mp = self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH]
                try:
                    mp.refresh_mode = {
                        'cyclic':     mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC,
                        'adaptive':   mmal.MMAL_VIDEO_INTRA_REFRESH_ADAPTIVE,
                        'both':       mmal.MMAL_VIDEO_INTRA_REFRESH_BOTH,
                        'cyclicrows': mmal.MMAL_VIDEO_INTRA_REFRESH_CYCLIC_MROWS,
                        }[intra_refresh]
                except KeyError:
                    raise PiCameraValueError(
                        "Invalid intra_refresh %s" % intra_refresh)
                self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_INTRA_REFRESH] = mp

        elif format == 'mjpeg':
            self.output_port.bitrate = bitrate
            self.output_port.commit()
            # MJPEG doesn't have an intra_period setting as such, but as every
            # frame is a full-frame, the intra_period is effectively 1
            self._intra_period = 1

        if quality:
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_INITIAL_QUANT] = quality
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MIN_QUANT] = quality
            self.output_port.params[mmal.MMAL_PARAMETER_VIDEO_ENCODE_MAX_QUANT] = quality

        self.encoder.inputs[0].params[mmal.MMAL_PARAMETER_VIDEO_IMMUTABLE_INPUT] = True
        self.encoder.enable()

    def start(self, output, motion_output=None):
        """
        Extended to initialize video frame meta-data tracking.
        """
        self.frame = PiVideoFrame(
                index=0,
                frame_type=None,
                frame_size=0,
                video_size=0,
                split_size=0,
                timestamp=0,
                complete=False,
                )
        if motion_output is not None:
            self._open_output(motion_output, PiVideoFrameType.motion_data)
        super(PiVideoEncoder, self).start(output)

    def stop(self):
        super(PiVideoEncoder, self).stop()
        self._close_output(PiVideoFrameType.motion_data)

    def request_key_frame(self):
        """
        Called to request an I-frame from the encoder.

        This method is called by :meth:`~PiCamera.request_key_frame` and
        :meth:`split` to force the encoder to output an I-frame as soon as
        possible.
        """
        self.encoder.control.params[mmal.MMAL_PARAMETER_VIDEO_REQUEST_I_FRAME] = True

    def split(self, output, motion_output=None):
        """
        Called to switch the encoder's output.

        This method is called by :meth:`~PiCamera.split_recording` and
        :meth:`~PiCamera.record_sequence` to switch the encoder's
        :attr:`output` object to the *output* parameter (which can be a
        filename or a file-like object, as with :meth:`start`).
        """
        with self.outputs_lock:
            outputs = {}
            if output is not None:
                outputs[PiVideoFrameType.frame] = output
            if motion_output is not None:
                outputs[PiVideoFrameType.motion_data] = motion_output
            self._next_output.append(outputs)
        # intra_period / framerate gives the time between I-frames (which
        # should also coincide with SPS headers). We multiply by three to
        # ensure the timeout is deliberately excessive, and clamp the minimum
        # timeout to 10 seconds (otherwise unencoded formats tend to fail
        # presumably due to I/O capacity)
        if self.parent:
            framerate = self.parent.framerate + self.parent.framerate_delta
        else:
            framerate = self.input_port.framerate
        timeout = max(15.0, float(self._intra_period / framerate) * 3.0)
        if self._intra_period > 1:
            self.request_key_frame()
        if not self.event.wait(timeout):
            raise PiCameraRuntimeError('Timed out waiting for a split point')
        self.event.clear()

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Extended to implement video frame meta-data tracking, and to handle
        splitting video recording to the next output when :meth:`split` is
        called.
        """
        self.frame = PiVideoFrame(
            index=
                self.frame.index + 1
                if self.frame.complete else
                self.frame.index,
            frame_type=
                PiVideoFrameType.key_frame
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_KEYFRAME else
                PiVideoFrameType.sps_header
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG else
                PiVideoFrameType.motion_data
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                PiVideoFrameType.frame,
            frame_size=
                buf.length
                if self.frame.complete else
                self.frame.frame_size + buf.length,
            video_size=
                self.frame.video_size
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.video_size + buf.length,
            split_size=
                self.frame.split_size
                if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO else
                self.frame.split_size + buf.length,
            timestamp=
                None
                if buf.pts in (0, mmal.MMAL_TIME_UNKNOWN) else
                buf.pts,
            complete=
                bool(buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END),
            )
        if self._intra_period == 1 or (buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CONFIG):
            with self.outputs_lock:
                try:
                    new_outputs = self._next_output.pop(0)
                except IndexError:
                    new_outputs = None
            if new_outputs:
                for new_key, new_output in new_outputs.items():
                    self._close_output(new_key)
                    self._open_output(new_output, new_key)
                    if new_key == PiVideoFrameType.frame:
                        self.frame = PiVideoFrame(
                                index=self.frame.index,
                                frame_type=self.frame.frame_type,
                                frame_size=self.frame.frame_size,
                                video_size=self.frame.video_size,
                                split_size=0,
                                timestamp=self.frame.timestamp,
                                complete=self.frame.complete,
                                )
                self.event.set()
        if buf.flags & mmal.MMAL_BUFFER_HEADER_FLAG_CODECSIDEINFO:
            key = PiVideoFrameType.motion_data
        return super(PiVideoEncoder, self)._callback_write(buf, key)


class PiCookedVideoEncoder(PiVideoEncoder):
    """
    Video encoder for encoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and only exists to
    provide naming symmetry with the image encoder classes.
    """


class PiRawVideoEncoder(PiRawMixin, PiVideoEncoder):
    """
    Video encoder for unencoded recordings.

    This class is a derivative of :class:`PiVideoEncoder` and the
    :class:`PiRawMixin` class intended for use with
    :meth:`~PiCamera.start_recording` when it is called with an unencoded
    format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """

    def _create_encoder(self, format):
        super(PiRawVideoEncoder, self)._create_encoder(format)
        # Raw formats don't have an intra_period setting as such, but as every
        # frame is a full-frame, the intra_period is effectively 1
        self._intra_period = 1


class PiImageEncoder(PiEncoder):
    """
    Encoder for image capture.

    This derivative of :class:`PiEncoder` extends the :meth:`_create_encoder`
    method to configure the encoder for a variety of encoded image outputs
    (JPEG, PNG, etc.).
    """

    encoder_type = mo.MMALImageEncoder

    def _create_encoder(
            self, format, quality=85, thumbnail=(64, 48, 35), restart=0):
        """
        Extends the base :meth:`~PiEncoder._create_encoder` implementation to
        configure the image encoder for JPEG, PNG, etc.
        """
        super(PiImageEncoder, self)._create_encoder(format)

        try:
            self.output_port.format = {
                'jpeg': mmal.MMAL_ENCODING_JPEG,
                'png':  mmal.MMAL_ENCODING_PNG,
                'gif':  mmal.MMAL_ENCODING_GIF,
                'bmp':  mmal.MMAL_ENCODING_BMP,
                }[format]
        except KeyError:
            raise PiCameraValueError("Unsupported format %s" % format)
        self.output_port.commit()

        if format == 'jpeg':
            self.output_port.params[mmal.MMAL_PARAMETER_JPEG_Q_FACTOR] = quality
            if restart > 0:
                # Don't set if zero as old firmwares don't support this param
                self.output_port.params[mmal.MMAL_PARAMETER_JPEG_RESTART_INTERVAL] = restart
            if thumbnail is None:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    0, 0, 0, 0)
            else:
                mp = mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T(
                    mmal.MMAL_PARAMETER_HEADER_T(
                        mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION,
                        ct.sizeof(mmal.MMAL_PARAMETER_THUMBNAIL_CONFIG_T)
                        ),
                    1, *thumbnail)
            self.encoder.control.params[mmal.MMAL_PARAMETER_THUMBNAIL_CONFIGURATION] = mp

        self.encoder.enable()


class PiOneImageEncoder(PiImageEncoder):
    """
    Encoder for single image capture.

    This class simply extends :meth:`~PiEncoder._callback_write` to terminate
    capture at frame end (i.e. after a single frame has been received).
    """

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        return (
            super(PiOneImageEncoder, self)._callback_write(buf, key)
            ) or bool(
            buf.flags & (
                mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
            )


class PiMultiImageEncoder(PiImageEncoder):
    """
    Encoder for multiple image capture.

    This class extends :class:`PiImageEncoder` to handle an iterable of outputs
    instead of a single output. The :meth:`~PiEncoder._callback_write` method
    is extended to terminate capture when the iterable is exhausted, while
    :meth:`PiEncoder._open_output` is overridden to begin iteration and rely
    on the new :meth:`_next_output` method to advance output to the next item
    in the iterable.
    """

    def _open_output(self, outputs, key=PiVideoFrameType.frame):
        self._output_iter = iter(outputs)
        self._next_output(key)

    def _next_output(self, key=PiVideoFrameType.frame):
        """
        This method moves output to the next item from the iterable passed to
        :meth:`~PiEncoder.start`.
        """
        self._close_output(key)
        super(PiMultiImageEncoder, self)._open_output(next(self._output_iter), key)

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        try:
            if (
                super(PiMultiImageEncoder, self)._callback_write(buf, key)
                ) or bool(
                buf.flags & (
                    mmal.MMAL_BUFFER_HEADER_FLAG_FRAME_END |
                    mmal.MMAL_BUFFER_HEADER_FLAG_TRANSMISSION_FAILED)
                ):
                self._next_output(key)
            return False
        except StopIteration:
            return True


class PiCookedOneImageEncoder(PiOneImageEncoder):
    """
    Encoder for "cooked" (encoded) single image output.

    This encoder extends :class:`PiOneImageEncoder` to include Exif tags in the
    output.
    """

    exif_encoding = 'ascii'

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiCookedOneImageEncoder, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        if parent:
            self.exif_tags = self.parent.exif_tags
        else:
            self.exif_tags = {}

    def _add_exif_tag(self, tag, value):
        # Format the tag and value into an appropriate bytes string, encoded
        # with the Exif encoding (ASCII)
        if isinstance(tag, str):
            tag = tag.encode(self.exif_encoding)
        if isinstance(value, str):
            value = value.encode(self.exif_encoding)
        elif isinstance(value, datetime.datetime):
            value = value.strftime('%Y:%m:%d %H:%M:%S').encode(self.exif_encoding)
        # MMAL_PARAMETER_EXIF_T is a variable sized structure, hence all the
        # mucking about with string buffers here...
        buf = ct.create_string_buffer(
            ct.sizeof(mmal.MMAL_PARAMETER_EXIF_T) + len(tag) + len(value) + 1)
        mp = ct.cast(buf, ct.POINTER(mmal.MMAL_PARAMETER_EXIF_T))
        mp[0].hdr.id = mmal.MMAL_PARAMETER_EXIF
        mp[0].hdr.size = len(buf)
        if (b'=' in tag or b'\x00' in value):
            data = tag + value
            mp[0].keylen = len(tag)
            mp[0].value_offset = len(tag)
            mp[0].valuelen = len(value)
        else:
            data = tag + b'=' + value
        ct.memmove(mp[0].data, data, len(data))
        self.output_port.params[mmal.MMAL_PARAMETER_EXIF] = mp[0]

    def start(self, output):
        timestamp = datetime.datetime.now()
        timestamp_tags = (
            'EXIF.DateTimeDigitized',
            'EXIF.DateTimeOriginal',
            'IFD0.DateTime')
        # Timestamp tags are always included with the value calculated
        # above, but the user may choose to override the value in the
        # exif_tags mapping
        for tag in timestamp_tags:
            self._add_exif_tag(tag, self.exif_tags.get(tag, timestamp))
        # All other tags are just copied in verbatim
        for tag, value in self.exif_tags.items():
            if not tag in timestamp_tags:
                self._add_exif_tag(tag, value)
        super(PiCookedOneImageEncoder, self).start(output)


class PiCookedMultiImageEncoder(PiMultiImageEncoder):
    """
    Encoder for "cooked" (encoded) multiple image output.

    This encoder descends from :class:`PiMultiImageEncoder` but includes no
    new functionality as video-port based encodes (which is all this class
    is used for) don't support Exif tag output.
    """
    pass


class PiRawImageMixin(PiRawMixin, PiImageEncoder):
    """
    Mixin class for "raw" (unencoded) image capture.

    The :meth:`_callback_write` method is overridden to manually calculate when
    to terminate output.
    """

    def __init__(
            self, parent, camera_port, input_port, format, resize, **options):
        super(PiRawImageMixin, self).__init__(
                parent, camera_port, input_port, format, resize, **options)
        self._image_size = 0

    def _callback_write(self, buf, key=PiVideoFrameType.frame):
        """
        Overridden to manually calculate when to terminate capture (see
        comments in :meth:`__init__`).
        """
        if self._image_size > 0:
            super(PiRawImageMixin, self)._callback_write(buf, key)
            self._image_size -= buf.length
        return self._image_size <= 0

    def start(self, output):
        self._image_size = self._frame_size
        super(PiRawImageMixin, self).start(output)


class PiRawOneImageEncoder(PiOneImageEncoder, PiRawImageMixin):
    """
    Single image encoder for unencoded capture.

    This class is a derivative of :class:`PiOneImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~PiCamera.capture` (et al) when it is called with an unencoded image
    format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    pass


class PiRawMultiImageEncoder(PiMultiImageEncoder, PiRawImageMixin):
    """
    Multiple image encoder for unencoded capture.

    This class is a derivative of :class:`PiMultiImageEncoder` and the
    :class:`PiRawImageMixin` class intended for use with
    :meth:`~PiCamera.capture_sequence` when it is called with an unencoded
    image format.

    .. warning::

        This class creates an inheritance diamond. Take care to determine the
        MRO of super-class calls.
    """
    def _next_output(self, key=PiVideoFrameType.frame):
        super(PiRawMultiImageEncoder, self)._next_output(key)
        self._image_size = self._frame_size

