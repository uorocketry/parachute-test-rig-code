from Phidget22.Phidget import * 
from Phidget22.Devices.VoltageRatioInput import *
import time
import csv
import keyboard  # Import the keyboard module

import serial
import serial.tools.list_ports
import keyboard
import datetime

#"""""""""""""""""""""""""DATAQ functions & Definitions"""""""""""""""""""""""""""

slist = [0x0000,0x0001]    
# Analog ranges for model DI-2108 (fixed ±10 V measurement range)
analog_ranges = [10]
rate_ranges = tuple((50000,20000,10000,5000,2000,1000,500,200,100,50,20,10))

# This is a list of analog and rate ranges to apply in slist order
range_table = list(())

ser=serial.Serial()
# Define flag to indicate if acquiring is active 
acquiring = False

""" Discover DATAQ Instruments devices and models.  Note that if multiple devices are connected, only the 
device discovered first is used. We leave it to you to ensure that it's the desired device model."""
def discovery():
    # Get a list of active com ports to scan for possible DATAQ Instruments devices
    available_ports = list(serial.tools.list_ports.comports())
    # Will eventually hold the com port of the detected device, if any
    hooked_port = "" 
    for p in available_ports:
        # Do we have a DATAQ Instruments device?
        if ("VID:PID=0683" in p.hwid):
            # Yes!  Dectect and assign the hooked com port
            hooked_port = p.device
            break

    if hooked_port:
        print("Found a DATAQ Instruments device on",hooked_port)
        ser.timeout = 0
        ser.port = hooked_port
        ser.baudrate = '115200'
        ser.open()
        return(True)
    else:
        # Get here if no DATAQ Instruments devices are detected
        print("Please connect a DATAQ Instruments device")
        input("Press ENTER to try again...")
        return(False)

# Sends a passed command string after appending <cr>
def send_cmd(command):
    ser.write((command+'\r').encode())
    time.sleep(.1)
    if not(acquiring):
        # Echo commands if not acquiring
        while True:
            if(ser.inWaiting() > 0):
                while True:
                    try:
                        s = ser.readline().decode()
                        s = s.strip('\n')
                        s = s.strip('\r')
                        s = s.strip(chr(0))
                        break
                    except:
                        continue
                if s != "":
                    print (s)
                    break

# Configure the instrment's scan list
def config_scn_lst():
    # Scan list position must start with 0 and increment sequentially
    position = 0 
    for item in slist:
        send_cmd("slist "+ str(position ) + " " + str(item))
        position += 1
        # Update the Range table
        if ((item) & (0xf)) < 8:
            # This is an analog channel. Refer to the slist prototype for your instrument
            # as defined in the instrument protocol. 
            range_table.append(analog_ranges[item >> 8])

        elif ((item) & (0xf)) == 8:
            # This is a dig in channel. No measurement range support. 
            # Update range_table with any value to keep it aligned.
            range_table.append(0) 

        elif ((item) & (0xf)) == 9:
            # This is a rate channel
            # Rate ranges begin with 1, so subtract 1 to maintain zero-based index
            # in the rate_ranges tuple
            range_table.append(rate_ranges[(item >> 8)-1]) 

        else:
            # This is a count channel. No measurement range support.
            # Update range_table with any value to keep it aligned.
            range_table.append(0)



"""""""""""""""""""""""""""""""""Phidget functions & Definitions"""""""""""""""""""""""""""""""""

# Define unique gains and offsets for each channel
gains = [38835, 39000, 39500, 39500]  
offsets = [-0.000050448, -0.000051000, -0.000053000, -0.000053000] # offset values for 4 channels

calibrated = [True, True, True, True]  # Calibration status for each channel

# Data structure to hold the weight for all 4 channels
weights = [0.0, 0.0, 0.0, 0.0]
z_avg = (weights[0] + weights[1])/2

# CSV file to log data
csv_file = "Load_Logs.csv"

# Callback function to process data from each channel
def onVoltageRatioChange(self, voltageRatio):
    channel = self.getChannel()  # Get the channel number

    if calibrated[channel]:
        # Apply the calibration parameters (gain, offset) to the raw voltage ratio
        weights[channel] = round(((voltageRatio - offsets[channel]) * gains[channel]), 4) 
        print(f"Channel {channel}: Weight: {weights[channel]}")
    else:
        # Just print the raw voltage ratio before calibration
        print(f"Channel {channel}: Uncalibrated")

# Function to tare each channel (calculate the offset)
def tareScale(ch, channel_num):    
    global offsets, calibrated
    num_samples = 16

    for i in range(num_samples):
        offsets[channel_num] += ch.getVoltageRatio()
        time.sleep(ch.getDataInterval()/1000.0)
        
    offsets[channel_num] /= num_samples
    calibrated[channel_num] = True

# Function to log data into the CSV file
def log_data_to_csv(elapsed_time):
    global weights, z_avg
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Time (s)", "Weight z (main)", "Weight x", "Weight y"])

        start_time = time.time()

        try:
            while True:
                writer.writerow([f"{elapsed_time:.2f}", z_avg, weights[2], weights[3]])
                
                
                # Check if 's' key is pressed to stop logging
                if keyboard.is_pressed('s'):
                    print("Logging stopped.")
                    break
                

        except (Exception, KeyboardInterrupt):
            pass
            print("Logging stopped.")



""""""""""""""""""""""""""""""""""""""""Main program"""""""""""""""""""""""""""""""""""""""""

def main():

    channels = []

    # Initialize 4 channels for the PhidgetBridge
    for i in range(4):
        voltageRatioInput = VoltageRatioInput()
        voltageRatioInput.setChannel(i)
        voltageRatioInput.setOnVoltageRatioChangeHandler(onVoltageRatioChange)
        voltageRatioInput.openWaitForAttachment(5000)  # Wait up to 5 seconds to attach
        voltageRatioInput.setDataInterval(750)  # Set data interval to 250ms
        
        channels.append(voltageRatioInput)
        print(f"Taring channel {i}")
        tareScale(voltageRatioInput, i)  # Tare (calibrate) each channel
        print(f"Channel {i} taring complete")

    print("Taring complete for all channels.")
    with open('combined_data.csv', mode='w', encoding="utf-8") as combined:
        combinedwriter = csv.writer(combined)
        combinedwriter.writerow(['Timestamp', 'Wind Speed (m/s)', 'Wind Direction (�)', 'Weight z(N)', 'Load x(N)', 'Load y(N)'])    
        with open('anemometer.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Days', 'Seconds', 'Wind Speed (m/s)', 'Wind Direction (°: N(180)/S(360,0)/E(270)/W(90))'])

            start_time = time.monotonic()  # Use a monotonic clock to track elapsed time
            last_log_time = start_time  # Track last logged time

            while discovery() == False:
                discovery()

            send_cmd("stop")
            send_cmd("encode 0")
            send_cmd("ps 0")   
            config_scn_lst()
            send_cmd("dec 512")
            send_cmd("srate 11718")

            print("\nReady to acquire...\n")
            print("Press <g> to go, <s> to stop, <r> to reset counter, and <q> to quit:")

            slist_pointer = 0
            output_string = ""

            # Initialize variables
            wind_speed = None
            wind_direction = None
            acquiring = False

            # Ensure first data point at elapsed_time = 0
            writer.writerow([0, 0.00000, 0.00000, 0.00000])
            file.flush()
            print(f"Logged: 0s, 0.00000 m/s, 0.00000°")

            while True:
                # Handle user input
                if keyboard.is_pressed('g' or 'G'):
                    keyboard.read_key()
                    acquiring = True
                    send_cmd("start")
                    start_time = time.monotonic()  # Reset timer
                    last_log_time = start_time

                if keyboard.is_pressed('s' or 'S'):
                    keyboard.read_key()
                    send_cmd("stop")
                    ser.flushInput()
                    print("\nStopped")
                    acquiring = False

                if keyboard.is_pressed('q' or 'Q'):
                    keyboard.read_key()
                    send_cmd("stop")
                    ser.flushInput()
                    break

                if acquiring:
                    # Read incoming data
                    while ser.inWaiting() > len(slist):
                        for i in range(len(slist)):
                            function = (slist[slist_pointer]) & (0xf)
                            bytes_data = ser.read(2)

                            if function < 8:
                                min_voltage = 1.32  
                                max_voltage = 6.6  
                                result = range_table[slist_pointer] * int.from_bytes(bytes_data, byteorder='little', signed=True) / 32768

                                if slist_pointer == 0:
                                    new_wind_speed = max(0, min(40, (result - min_voltage) / (max_voltage - min_voltage) * 40))
                                    wind_speed = new_wind_speed
                                    output_string += "Wind Speed: {: 3.5f} m/s, ".format(wind_speed)

                                elif slist_pointer == 1:
                                    new_wind_direction = ((result - min_voltage) / (max_voltage - min_voltage) * 360 + 8.2) % 360
                                    wind_direction = new_wind_direction
                                    output_string += "Wind Direction: {: 3.5f}°, ".format(wind_direction)

                            slist_pointer += 1
                            if slist_pointer >= len(slist):
                                output_string = ""
                                slist_pointer = 0

                                # Check if 0.5s has elapsed
                                current_time = time.monotonic()
                                if current_time - last_log_time >= 0.5:
                                    elapsed_time = current_time - start_time
                                    writer.writerow([0, round(elapsed_time, 5), round(wind_speed, 5), round(wind_direction, 5)])
                                    file.flush()
                                    # Start logging data to CSV file
                                    log_data_to_csv(elapsed_time)
                                    print(f"Logged: {elapsed_time:.2f}s, {wind_speed:.5f} m/s, {wind_direction:.5f}°")

                                    combinedwriter.writerow([round(elapsed_time, 5), round(wind_speed, 5), round(wind_direction, 5), z_avg, weights[2], weights[3]])
                                    last_log_time = current_time  # Update last log time

        ser.close()



    # Close all channels when done
    for ch in channels:
        ch.close()
        print(f"Channel {ch.getChannel()} closed.")

if __name__ == "__main__":
    main()
