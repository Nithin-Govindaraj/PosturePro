### Circuit Diagram 

> Power Input: 5V 5A Adapter → Raspberry Pi 4B via USB-C
> All components draw power through Raspberry Pi GPIO pins

   <Images/Circuit Diagram.png/>


 ### Wiring Summary

| Component       | Pi Pin          | Connection                      |
|-----------------|-----------------|---------------------------------|
| SIM800L VCC     | PIN 2 (5V)      | Direct + 10µF 25V capacitor     |
| SIM800L GND     | PIN 34 (GND)    | Direct                          |
| SIM800L RXD     | GPIO 14 (TXD)   | Direct                          |
| SIM800L TXD     | GPIO 15 (RXD)   | Via 1KΩ + 2KΩ voltage divider   |
| Buzzer (+)      | GPIO 17         | Direct (3.3V Active Piezo)      |
| Buzzer (-)      | PIN 9 (GND)     | Direct                          |
| USB Webcam      | USB PORT 2      | Direct                          |
| USB Microphone  | USB PORT 1      | Direct                          |

> **Note:** Ensure 5V 5A adapter is used.
> Underpowered supply may cause Pi to reboot.
