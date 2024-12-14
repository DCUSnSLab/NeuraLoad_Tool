char inputData;
char ahrsData;
String ahrsString = "";
boolean stringCheck = false;

void setup() {
  Serial.println("Initializing...");
  Serial.begin(115200);       // Communication with Serial Monitor
  Serial1.begin(115200);      // Communication with iAHRS IMU
  Serial2.begin(115200);      // Communication with Laser sensor

  // iAHRS initialization commands
  Serial1.println("b1=9600");
  delay(100);
  Serial1.println("so=0");    // Enable data transmission via RS-232 port
  delay(100);
  Serial1.println("sp=10");   // Set data transmission period to 10ms
  delay(100);
  Serial1.println("sd=0x0004"); // Set data types: acceleration, velocity, position, vibration
  delay(100);

  Serial.println("setup complete");
  delay(4000);
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
    Serial1.write(inputData);        // Send input to iAHRS
  }

  // Read data from iAHRS
  readFromIMU();
  
  // Read data from Laser sensor
  if (Serial2.available() >= 9) {    // Check if 9 bytes of data are available
    uint8_t buf[9];
    for (int i = 0; i < 9; i++) {
      buf[i] = Serial2.read();      // Read data from Laser sensor
    }

    // Check for packet start
    if (buf[0] == 0x59 && buf[1] == 0x59) {
      int distance = buf[2] + (buf[3] << 8);  // Calculate distance
      Serial.print("Laser: ");
      Serial.println(distance);

      if (distance > 10000 || distance < 0) {
        Serial.println("Error: Invalid distance detected. Rebooting...");
        // Watchdog Timer configuration required for Mega
        while (1);  // Infinite loop
      }
    }
  }
}

void readFromIMU() {
  while (Serial1.available()) { // Check if data is available from iAHRS
    ahrsData = (char)Serial1.read(); // Read data byte by byte
    if (ahrsData == '\n' && ahrsString.length() > 0) { // If end of data line and non-empty string
      stringCheck = true;   // Set data received flag
      return;
    } else if (ahrsData != '\r') {
      ahrsString += ahrsData;
    }
  }
}
