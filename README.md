# Intelligent Feeding and Access System for Cats

This repository contains the source code and configuration files for an intelligent feeding and access system for cats. The system uses a Raspberry Pi 5 as the main control unit, a web camera for cat detection with YOLOv8, a relay-driven solenoid for door access, a PIR motion sensor for presence detection, an LED strip for ambient lighting, an SG90 servo motor for food dispensing, MQTT for communication, and a Node-RED dashboard for manual control and monitoring.

## Repository Link

Public repository:

```text
https://github.com/nevee7/Thesis
```

## Project Deliverables

The project deliverables are:

- Python source code for the Raspberry Pi control application.
- Node-RED dashboard/flow configuration for manual control and monitoring.
- MQTT topic structure used for communication between the Python application and Node-RED.
- Setup and launch instructions for Raspberry Pi OS.
- Hardware pin mapping used by the control script.

Main implemented functions:

- Real-time cat detection using a web camera and YOLOv8 nano.
- Automatic door opening using a relay-controlled 12V solenoid.
- Automatic lighting control using a PIR motion sensor and relay-controlled LED strip.
- Food dispensing using an SG90 servo motor and a 3D printed mechanism.
- Manual door, light, and servo control through Node-RED.
- MQTT-based state synchronization between the Python script and the dashboard.

## Hardware Requirements

- Raspberry Pi 5, 8 GB RAM recommended.
- Raspberry Pi OS.
- USB web camera.
- PIR SR602 motion sensor.
- 2-channel 5V relay module.
- 12V solenoid lock.
- 12V LED strip.
- SG90 servo motor.
- 12V power supply.
- Buck converter for reducing 12V to 5V for the servo motor.
- 3D printed food dispensing mechanism.
- Wires, connectors, breadboard or soldered circuit, and mechanical enclosure.

## Pin Mapping

The annex source code uses the following Raspberry Pi GPIO pins:

| Component | GPIO Pin | Purpose |
|---|---:|---|
| Solenoid relay | GPIO 27 | Opens/closes the access door |
| PIR sensor | GPIO 17 | Detects motion inside the shelter |
| LED strip relay | GPIO 22 | Turns ambient lighting on/off |
| SG90 servo motor | GPIO 18 | Controls food dispensing through PWM |

If the physical wiring is changed, update the pin constants in the Python script before launching the application.

## MQTT Topics

The application uses Mosquitto as the MQTT broker, running locally on the Raspberry Pi.

| Topic | Direction | Payload | Description |
|---|---|---|---|
| `home/catdoor/door_status` | Python -> Node-RED | `1` or `0` | Publishes the current door state |
| `home/catdoor/light_status` | Python -> Node-RED | `1` or `0` | Publishes the current light state |
| `home/catdoor/door_manual` | Node-RED -> Python | `1` or `0` | Manual door open/close command |
| `home/catdoor/light_manual` | Node-RED -> Python | `1` or `0` | Manual light on/off command |
| `home/catdoor/servo_position` | Node-RED -> Python | Angle value | Sets the servo position, for example `90` or `180` |

## Application Build Steps

This is a Python-based Raspberry Pi application, so there is no compilation step. Building the application means preparing the runtime environment, installing dependencies, and downloading the YOLOv8 model.

1. Update Raspberry Pi OS:

```bash
sudo apt update
sudo apt upgrade -y
```

2. Install Python and system packages:

```bash
sudo apt install -y python3 python3-pip python3-venv mosquitto mosquitto-clients
```

3. Enable and start Mosquitto:

```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

4. Install Node-RED:

```bash
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
```

5. Enable Node-RED at startup:

```bash
sudo systemctl enable nodered.service
sudo systemctl start nodered.service
```

6. Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

7. Install Python dependencies:

```bash
pip install --upgrade pip
pip install ultralytics opencv-python lgpio gpiozero paho-mqtt
```

8. Download or prepare the YOLOv8 nano model:

```bash
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

The model file `yolov8n.pt` is used by the application for cat detection. If the Raspberry Pi has no internet connection during installation, copy the model file manually into the project directory.

## Application Installation Steps

1. Clone the public repository:

```bash
git clone https://github.com/nevee7/Thesis
cd Thesis
```

2. Connect the hardware according to the pin mapping listed above.

3. Make sure the 12V power circuit is separated from the Raspberry Pi GPIO control circuit through the relay module.

4. Make sure the servo motor is powered from a stable 5V source, such as a buck converter, and that the servo ground and Raspberry Pi ground share a common reference.

5. Start Mosquitto and Node-RED if they are not already running:

```bash
sudo systemctl start mosquitto
sudo systemctl start nodered.service
```

6. Import the Node-RED flow from the repository, if provided, into the Node-RED editor:

```text
http://<raspberry-pi-ip>:1880
```

The dashboard can then be accessed from the Node-RED dashboard interface.

## Application Launch Steps

1. Activate the Python environment:

```bash
source .venv/bin/activate
```

2. Launch the main control script:

```bash
python3 main.py
```

3. Open the Node-RED dashboard in a browser:

```text
http://<raspberry-pi-ip>:1880/ui
```

4. Use the dashboard to monitor and manually control:

- Door state.
- Light state.
- Door open/close command.
- Light on/off command.
- Servo position for feeding.

5. To stop the Python application, press `Esc` in the OpenCV video window or stop the process from the terminal with `Ctrl+C`.

## Runtime Behavior

When the application starts, it initializes the servo motor, connects to the local MQTT broker, starts the PIR motion monitoring thread, loads the YOLOv8 nano model, and opens the camera stream.

During operation:

- Each camera frame is processed by YOLOv8.
- If a cat is detected with confidence greater than `0.5`, the system opens the door if it is not already open.
- The solenoid is activated through the relay and the door remains open for a defined interval.
- The PIR sensor controls the LED strip automatically.
- MQTT commands from Node-RED can manually control the door, light, and servo.
- Manual commands use override logic to prevent conflicts with automatic actions.
