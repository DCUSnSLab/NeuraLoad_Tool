#include <SoftwareSerial.h>

// SoftwareSerial setup (RX: pin 7, TX: pin 6)
#define RX_PIN 7
#define TX_PIN 6
SoftwareSerial imuSerial(RX_PIN, TX_PIN);

char inputData;
char ahrsData;  
String ahrsString = "";         
boolean stringCheck = false;

void setup() {
  Serial.begin(115200);        // Communication with Serial Monitor
  imuSerial.begin(115200);     // Communication with iAHRS

  Serial.println("Initializing iAHRS...");

  // iAHRS initialization commands
  imuSerial.println("so=0");    // Enable data transmission via RS-232 port
  delay(100);
  imuSerial.println("sp=1000"); // Set data transmission period to 1000ms
  delay(100);
  imuSerial.println("sd=0x0004"); // Set data types: acceleration, velocity, position, vibration
  delay(1000);

  Serial.println("iAHRS setup complete");
}

void loop() {  
  // Output data received from iAHRS
  if (stringCheck) {
    Serial.println(ahrsString); // Print ahrsString
    ahrsString = "";            // Reset ahrsString
    stringCheck = false;        // Reset flag
  }

  // Send commands from Serial Monitor to iAHRS
  if (Serial.available()) {
    inputData = (char)Serial.read(); // Read input from Serial Monitor
    imuSerial.write(inputData);      // Send input to iAHRS
  }

  // Read data from iAHRS
  readFromIMU();
}

void readFromIMU() {
  while (imuSerial.available()) { // Check if data is available from iAHRS
    ahrsData = (char)imuSerial.read(); // Read data byte by byte
    if (ahrsData == '\n' && ahrsString.length() > 0) { // If end of data line and non-empty string
      stringCheck = true;   // Set data received flag
      return;
    } else if (ahrsData != '\r') {
      ahrsString += ahrsData;
    }
  }
}
