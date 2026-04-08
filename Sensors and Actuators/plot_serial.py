#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 25 15:38:03 2025

@author: lubos
"""
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
import serial
 
# try to find a serial port
# make sure to close Serial Monitor/Plotter in Arduino
port_ok = False
for i in range(4,5):
    try:
        port_name = "COM%d"%i
        #alternatives /dev/ttyUSB%d, COM%d, /dev/ttyS%d
        print(port_name)
        ser = serial.Serial(port_name,9600)
        print("Opened port "+port_name)
        port_ok = True
        break
    except serial.SerialException:
        pass
 
if (not(port_ok)):
    raise Exception("Failed to open port")

plt.close('all')
fig, ax = plt.subplots()
# equivalent but more general
line_plot = ax.plot([],[],linewidth=3,color='black')[0]

times = []
vals = []
val_min = 1e66
val_max = -1e66

def anim(n):
    global val_min, val_max
    global times, vals
    
    line = str(ser.readline()); # read line from serial port
    line = line[2:-5]  #eliminate trailing b' and \r\n
    pieces = line.split(',')
        
    time = float(pieces[0])
    val = float(pieces[1])
    print("%g, %g"%(time,val))
 
    if (len(pieces)==2):       # make sure we get a full line
        time = float(pieces[0])  # current time step
        val = float(pieces[1])  # read value
        
        # update min/max for value
        if (val<val_min):val_min = val
        if (val>val_max):val_max = val
        
        # append data
        times.append(time)
        vals.append(val)
        
        # update plot
        # line_plot.set_xdata(times)
        # line_plot.set_ydata(vals)
        
        # this is not the ideal way of doing this but works for now
        plt.cla();
        ax.plot(times,vals,linewidth=3,color='black')

        #print(vals)
        # output data range
       # print("ts: %d, val: %.1f"%(ts,val))
 
        # update image
       # im1.set_array(phi)
    
# back in "main", enable animation

anim = animation.FuncAnimation(fig, anim, frames=50, interval=.5, repeat=False,blit=False)

plt.show()   # show image