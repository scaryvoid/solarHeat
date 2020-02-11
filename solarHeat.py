#!/usr/bin/python2.7

import os, glob, time, datetime, argparse, sys, atexit
import RPi.GPIO as io

# make sure rpi is setup for 1 wire temp sensors
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# setup gpio for relay
io.setmode(io.BCM)
io.setup(26,io.OUT)
io.output(26,0)

deviceRoot = '/sys/bus/w1/devices/'
sHeater = deviceRoot + '28-0117b2d19dff/w1_slave'
sOutput = deviceRoot + '28-0417c1ad07ff/w1_slave'
sOutside = deviceRoot + '28-0417c1e598ff/w1_slave'
sIndoor = deviceRoot + '28-0417c20267ff/w1_slave'
sOther = deviceRoot + '28-0417c20627ff/w1_slave'
logPath = 'solarHeat.log'
tempLog = 'solarHeat.tmp'


def exit_handler():
    f = open(logPath, 'a')
    f.write("{0} Terminating\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    f.close()
    io.output(26,0)


def readFile(filepath):
    f = open(filepath, 'r')
    lines = f.readlines()
    f.close()
    return lines


def getTemp(filepath):
    lines = readFile(filepath)
    count = 0
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        count += 1
        lines = readFile(filepath)
        if count >= 5:
            io.output(26,0)
            with open(logPath, 'a') as f:
                f.write("Error: Lost contact with {0} Turning fan off and exiting...\n".format(filepath))
            sys.exit()

    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_f


def getCurTime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description='Run solar heater and log temperature data.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', help='Verbose', action='store_true')
    parser.add_argument('-s', metavar='<degrees F>', default=90, type=float, help='Start fan at or above this heater temp')
    parser.add_argument('-e', metavar='<degrees F>', default=65, type=float, help='Stop fan at or below this heater temp')
    parser.add_argument('-o', metavar='<degrees F>', default=-100, type=float, help='Stop fan below this output temp (optional)')    
    parser.add_argument('-t', metavar='<seconds n>', default=10, type=float, help='Time between polling sensors. NOTE: polling each sensor takes an additional second.')
    args = parser.parse_args()

    atexit.register(exit_handler)
    if os.path.exists(tempLog):
        os.remove(tempLog)
    with open(logPath, 'a') as f:
        f.write("{0} Program Start {1} {2} {3} {4}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), args.s, args.e, args.o, args.t))
    state = 0  # 1 = heating 0 = off
    lastOn = datetime.datetime.now()    
    while True:
        tHeater = float(getTemp(sHeater))
        tOutside = float(getTemp(sOutside))
        tOutput = float(getTemp(sOutput))

        printString = "{4} tHeater:{0:.2f} tOutput:{2:.2f} tOutside:{1:.2f} state:{3}\n".format(tHeater, tOutside, tOutput, state, getCurTime())
        if args.v:
            print printString
        with open(tempLog, 'a') as f:
            f.write(printString)

        if tHeater >= args.s and state is 0:
            printString = "{0} tHeater:{1:.2f} tOutput:{2:.2f} tOutside:{3:.2f} Starting Fan\n".format(getCurTime(), tHeater, tOutput, tOutside)
            if args.v:
                print printString
            with open(logPath, 'a') as f:                
                f.write(printString)
            with open(tempLog, 'a') as f:
                f.write(printString)
            io.output(26,1)
            state = 1
            lastOn = datetime.datetime.now()
        elif state is 1 and (tHeater <= args.e or tOutput <= args.o):
            onTime = datetime.datetime.now() - lastOn
            printString = "{0} tHeater:{1:.2f} tOutput:{2:.2f} tOutside:{3:.2f} Stopping Fan onTime:{4}\n".format(getCurTime(), tHeater, tOutput, tOutside, onTime)

            if args.v:
                print printString
            with open(logPath, 'a') as f:                
                f.write(printString)
            with open(tempLog, 'a') as f:
                f.write(printString)
            io.output(26,0)
            state = 0
        
        time.sleep(args.t)
        

if __name__ == "__main__":
    main()
