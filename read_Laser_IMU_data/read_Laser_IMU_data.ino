#include <SoftwareSerial.h>
#include <avr/wdt.h>

SoftwareSerial laserSerial(9, 8);
SoftwareSerial IMUSerial(3, 4);

unsigned long lastReadTime = 0;
const unsigned long readInterval = 1000;

void setup() {
  Serial.begin(9600);
  IMUSerial.begin(19200);
  laserSerial.begin(115200);
  wdt_enable(WDTO_2S);
}

void loop() {
  unsigned long currentTime = millis();

  if (currentTime - lastReadTime >= readInterval) {
    lastReadTime = currentTime;

    
  
    if (laserSerial.available() >= 9) {
      uint8_t buf[9];
      for(int i = 0; i < 9; i++) {
        buf[i] = laserSerial.read();
      }
  
      if (buf[0] == 0x59 && buf[1] == 0x59) {
        int distance = buf[2] + (buf[3] << 8);
  
//        Serial.println("Distance: ");
        Serial.println(distance);
  
        if(distance > 10000 || distance < 0) {
          Serial.println("Error: Invalid distance detected. Rebooting...");
          wdt_enable(WDTO_15MS);
          while (1);
        }
      }
    }
  
    if(IMUSerial.available()>=0) {
      uint8_t imuData = IMUSerial.read();
//      Serial.println("IMU Data: ");
      Serial.println(imuData, HEX);
      Serial.print(" ");
    }

    wdt_reset();
 }
}
