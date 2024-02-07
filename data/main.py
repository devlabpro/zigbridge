import serial
import time
import json

ArduinoSerial = serial.Serial('COM5',115200) 
time.sleep(2) 

def stateCheck(message):
   print(message)
   data = json.loads(message.replace("'",'"'))
   print("Cluster: {} | state: {}".format(data['cl'],data['st']))


while True:
    b = ArduinoSerial.readline()
    s1=  b.decode('utf-8').rstrip()  # convert to string
    check = s1.split("|")
    if len(check) > 2:
        print("Got state change:" ,check)
        stateCheck(check[1])
    else:
        print(s1)

ArduinoSerial.close() 