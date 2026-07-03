#!/usr/bin/env python3

import time
import threading

import cv2
import lgpio
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from gpiozero import OutputDevice, MotionSensor
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device


Device.pin_factory = LGPIOFactory()

BROKER_MQTT = "localhost"
PORT_MQTT = 1883

TOPIC_STARE_USA = "home/catdoor/door_status"
TOPIC_STARE_LUMINA = "home/catdoor/light_status"
TOPIC_CONTROL_USA = "home/catdoor/door_manual"
TOPIC_CONTROL_LUMINA = "home/catdoor/light_manual"
TOPIC_POZITIE_SERVO = "home/catdoor/servo_position"

PIN_SOLENOID = 27
PIN_PIR = 17
PIN_LUMINA = 22
PIN_SERVO = 18

SEC_DESCHIDERE_USA = 10
SEC_LUMINA = 5

FREQ_SERVO = 50
MIN_US = 500
MAX_US = 2500
PERIOADA_US = 1_000_000 // FREQ_SERVO

handle_lgpio = None

usa_deschisa = False
lumina_pornita = False
timer_usa = None

lock_stare = threading.Lock()
override_lumina = False
override_usa = False

client_mqtt = mqtt.Client(client_id="usa_pisica_pi5")

solenoid = OutputDevice(PIN_SOLENOID, active_high=True, initial_value=False)
releu_lumina = OutputDevice(PIN_LUMINA, active_high=True, initial_value=False)
pir = MotionSensor(PIN_PIR)


def unghi_la_duty(unghi: float) -> float:
    unghi = max(0.0, min(180.0, float(unghi)))
    puls = MIN_US + (unghi / 180.0) * (MAX_US - MIN_US)
    return (puls / PERIOADA_US) * 100.0


def init_servo():
    global handle_lgpio

    handle_lgpio = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_output(handle_lgpio, PIN_SERVO)
    lgpio.tx_pwm(handle_lgpio, PIN_SERVO, FREQ_SERVO, unghi_la_duty(90))


def set_servo(unghi: float):
    global handle_lgpio

    if handle_lgpio is None:
        return

    unghi = max(0.0, min(180.0, float(unghi)))
    duty = unghi_la_duty(unghi)

    lgpio.tx_pwm(handle_lgpio, PIN_SERVO, FREQ_SERVO, duty)
    time.sleep(0.3)
    lgpio.tx_pwm(handle_lgpio, PIN_SERVO, FREQ_SERVO, 0)


def oprire_servo():
    global handle_lgpio

    if handle_lgpio is None:
        return

    lgpio.tx_pwm(handle_lgpio, PIN_SERVO, FREQ_SERVO, 0)
    lgpio.gpiochip_close(handle_lgpio)


def stare_usa():
    return "1" if usa_deschisa else "0"


def stare_lumina():
    return "1" if lumina_pornita else "0"


def trimite_stare_usa():
    client_mqtt.publish(TOPIC_STARE_USA, stare_usa(), retain=True)


def trimite_stare_lumina():
    client_mqtt.publish(TOPIC_STARE_LUMINA, stare_lumina(), retain=True)


def deschide_usa(sursa="auto"):
    global usa_deschisa, timer_usa, override_usa

    with lock_stare:
        if timer_usa:
            timer_usa.cancel()

        usa_deschisa = True
        override_usa = sursa == "mqtt"
        solenoid.on()
        trimite_stare_usa()

        timer_usa = threading.Timer(
            SEC_DESCHIDERE_USA,
            inchide_usa,
            kwargs={"sursa": "timer"}
        )
        timer_usa.start()


def inchide_usa(sursa="auto"):
    global usa_deschisa, timer_usa, override_usa

    with lock_stare:
        if sursa == "mqtt":
            override_usa = True

            if timer_usa:
                timer_usa.cancel()
                timer_usa = None

            usa_deschisa = False
            solenoid.off()
            trimite_stare_usa()
            return

        if sursa == "timer":
            override_usa = False
            usa_deschisa = False
            solenoid.off()
            trimite_stare_usa()
            return

        if override_usa:
            return

        usa_deschisa = False
        solenoid.off()
        trimite_stare_usa()


def porneste_lumina(sursa="auto"):
    global lumina_pornita, override_lumina

    override_lumina = sursa == "mqtt"

    if not lumina_pornita:
        lumina_pornita = True
        releu_lumina.on()
        trimite_stare_lumina()


def opreste_lumina(sursa="auto"):
    global lumina_pornita, override_lumina

    if sursa == "mqtt":
        override_lumina = True
        lumina_pornita = False
        releu_lumina.off()
        trimite_stare_lumina()
        return

    if override_lumina:
        return

    lumina_pornita = False
    releu_lumina.off()
    trimite_stare_lumina()


def monitor_miscare():
    ultimul_moment = 0.0

    while True:
        if pir.motion_detected:
            ultimul_moment = time.time()
            porneste_lumina("auto")
        else:
            if lumina_pornita and (time.time() - ultimul_moment > SEC_LUMINA):
                opreste_lumina("auto")

        time.sleep(0.5)


def conectat(client, userdata, flags, rc):
    client.subscribe(TOPIC_CONTROL_USA)
    client.subscribe(TOPIC_CONTROL_LUMINA)
    client.subscribe(TOPIC_POZITIE_SERVO)


def mesaj(client, userdata, msg):
    payload = msg.payload.decode().strip()

    if msg.topic == TOPIC_CONTROL_USA:
        if payload == "1":
            deschide_usa("mqtt")
        else:
            inchide_usa("mqtt")

    elif msg.topic == TOPIC_CONTROL_LUMINA:
        if payload == "1":
            porneste_lumina("mqtt")
        else:
            opreste_lumina("mqtt")

    elif msg.topic == TOPIC_POZITIE_SERVO:
        try:
            set_servo(int(float(payload)))
        except:
            pass


client_mqtt.on_connect = conectat
client_mqtt.on_message = mesaj


def main():
    init_servo()

    client_mqtt.connect(BROKER_MQTT, PORT_MQTT, 60)
    client_mqtt.loop_start()

    threading.Thread(target=monitor_miscare, daemon=True).start()

    model = YOLO("yolov8n.pt")
    camera = cv2.VideoCapture(0)

    while True:
        ret, frame = camera.read()

        if not ret:
            continue

        rezultate = model(frame, verbose=False)
        pisica = False

        for r in rezultate:
            for box in r.boxes:
                cls = int(box.cls[0])

                if model.names[cls] == "cat" and float(box.conf[0]) > 0.5:
                    pisica = True

        if pisica and not usa_deschisa:
            deschide_usa("auto")

        cv2.imshow("Sistem Pisica", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    camera.release()
    cv2.destroyAllWindows()

    inchide_usa("auto")
    opreste_lumina("auto")
    oprire_servo()

    client_mqtt.loop_stop()
    client_mqtt.disconnect()


if __name__ == "__main__":
    main()
