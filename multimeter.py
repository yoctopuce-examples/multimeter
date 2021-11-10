#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys,re,socket,linecache
import yoctopuce

from yoctopuce.yocto_api import *
from yoctopuce.yocto_display import *
from yoctopuce.yocto_anbutton import *


# List of sensors to display (discovered by Plug-and-play)
sensors = { }
currentSensor = ""

def refreshDisplay():
    global currentSensor
    if currentSensor not in sensors:
        currentSensor = list(sensors.keys())[-1]
    sensor = sensors[currentSensor]
    dispLayer.clear()
    dispLayer.selectFont("Small.yfm")
    dispLayer.drawText(0,0,YDisplayLayer.ALIGN.TOP_LEFT,sensor["name"])
    dispLayer.selectFont("Medium.yfm")
    dispLayer.drawText(127,28,YDisplayLayer.ALIGN.BOTTOM_RIGHT,sensor["val"])
    display.copyLayerContent(1,2)

def deviceArrival(m):
    global sensors, currentSensor
    serial = m.get_serialNumber()
    print('Device arrival : ' + serial)
    # Alternate solution: register any kind of sensor on the device
    sensor = YSensor.FirstSensor()
    while sensor:
        if sensor.get_module().get_serialNumber() == serial:
            hardwareId = sensor.get_hardwareId()
            print('- ' + hardwareId)
            sensors[hardwareId] = \
                    { "name" : sensor.get_friendlyName(),
                      "val"  : sensor.get_unit() }
            currentSensor = hardwareId
            sensor.registerValueCallback(sensorChanged)
        sensor = sensor.nextSensor()

    refreshDisplay()

def sensorChanged(fct,value):
    hwId = fct.get_hardwareId()
    if hwId in sensors: sensors[hwId]['val'] = value+" "+fct.get_unit()
    refreshDisplay()

def deviceRemoval(m):
    deletePattern = m.get_serialNumber()+"\..*"
    deleteList = []
    for key in sensors:
        if re.match(deletePattern, key): deleteList.append(key)
    for key in deleteList:
        del sensors[key]
    refreshDisplay()

def buttonPressed(fct,value):
    global currentSensor
    if(int(value) > 500):    # button released
        fct.set_userData(False)
        return
    if(fct.get_userData()): # button was already pressed
        return
    # Button was pressed, cycle through sensors values
    fct.set_userData(True)
    delta = (1 if fct.get_hardwareId()[-1] == '1' else -1)
    if(delta != 0):
        keys = list(sensors.keys())
        print(keys)
        idx = len(keys)-1
        for i in range(len(keys)):
            if keys[i] == currentSensor:
                idx = (i+delta+len(keys)) % len(keys)
        currentSensor = keys[idx]
        refreshDisplay()


# Setup the API to use the local VirtualHub
errmsg=YRefParam()
if YAPI.RegisterHub("127.0.0.1", errmsg) != YAPI.SUCCESS:
    sys.exit("Init error: "+errmsg.value)

# Get the display object
display = YDisplay.FirstDisplay()
if display is None:
    sys.exit("Display not connected")
display.resetAll()
dispLayer = display.get_displayLayer(1)
dispLayer.hide()

# Get the buttons objects
serial = display.get_module().get_serialNumber()
prevButton = YAnButton.FindAnButton(serial+".anButton1")
nextButton = YAnButton.FindAnButton(serial+".anButton6")
prevButton.set_userData(False)
nextButton.set_userData(False)
prevButton.registerValueCallback(buttonPressed);
nextButton.registerValueCallback(buttonPressed);

# Put the Raspberry Pi itself as default sensor, to show IP address
sensors[""] = { "name" : socket.gethostname(),
                "val"  : socket.gethostname() }
print("Host: "+socket.gethostname())
refreshDisplay()

# Handle sensors plug-and-play events
YAPI.RegisterDeviceArrivalCallback(deviceArrival)
YAPI.RegisterDeviceRemovalCallback(deviceRemoval)
print('Hit Ctrl-C to Stop')
while True:
    YAPI.UpdateDeviceList(errmsg) # handle plug/unplug events
    YAPI.Sleep(500, errmsg)       # handle others events
