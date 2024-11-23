from Phidget22.Phidget import * 
from Phidget22.Devices.VoltageRatioInput import *
import time
import csv

# Define unique gains and offsets for each channel
gains = [38835, 39000, 39500, 39500]  # Example gain values for 4 channels
offsets = [-0.000050448, -0.000051000, -0.000053000, -0.000053000]  # Example offset values for 4 channels

calibrated = [False, False, False, False]  # Calibration status for each channel

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
        weights[channel] = round(((voltageRatio - offsets[channel]) * gains[channel]),4) 
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
def log_data_to_csv():
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Time (s)", "Channel 0 Weight", "Channel 1 Weight", "Channel 2 Weight", "Channel 3 Weight"])

        start_time = time.time()

        try:
            while True:
                elapsed_time = time.time() - start_time
                writer.writerow([f"{elapsed_time:.2f}", z_avg, weights[2], weights[3]])
                print(f"Logged at {elapsed_time:.2f} seconds")
                time.sleep(1)  # Record every second

        except (Exception, KeyboardInterrupt):
            pass
            print("Logging stopped.")
      
      
def vector_plot():
    import matplotlib.pyplot as plt
    import numpy as np
    from mpl_toolkits.mplot3d import Axes3D

    force_x = weights[2]
    force_y = weights[3]
    force_z = z_avg

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Origin point
    origin = np.array([[0, 0, 0]])

    # Force vector
    forces = np.array([[force_x, force_y, force_z]])

    # Plot the vector as an arrow
    ax.quiver(origin[:,0], origin[:,1], origin[:,2], forces[:,0], forces[:,1], forces[:,2], 
            color='b', arrow_length_ratio=0.1)

    # Set axis labels
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    ax.set_zlabel('Z Axis')

    # Set plot limits
    ax.set_xlim([0, max(force_x, 1)])
    ax.set_ylim([0, max(force_y, 1)])
    ax.set_zlim([0, max(force_z, 1)])

    plt.show()

# Main function to initialize channels and start data collection
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
    
    # Start logging data to CSV file
    log_data_to_csv()

    #plot vector_plot
    vector_plot()

    # Close all channels when done
    for ch in channels:
        ch.close()
        print(f"Channel {ch.getChannel()} closed.")

if __name__ == "__main__":
    main()
