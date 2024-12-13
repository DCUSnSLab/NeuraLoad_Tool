#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <cstdlib>
#include <regex>
#include <filesystem>
#include <chrono>
#include <thread>
#include <ctime>
#include <iomanip>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>

// Function to detect Arduino port
std::string detectArduinoPort() {
    std::string basePath = "/dev/";
    std::string detectedPort;

    // Iterate through /dev/ directory to find ttyACM* devices
    for (const auto& entry : std::filesystem::directory_iterator(basePath)) {
        if (entry.path().string().find("ttyACM") != std::string::npos) {
            std::string portName = entry.path().string();
            std::cout << "Checking port: " << portName << std::endl;

            // Run udevadm info to check for Arduino attributes
            std::ostringstream command;
            command << "udevadm info -a -n " << portName << " 2>/dev/null";

            FILE* pipe = popen(command.str().c_str(), "r");
            if (!pipe) {
                std::cerr << "Error: Unable to execute udevadm for " << portName << std::endl;
                continue;
            }

            char buffer[256];
            std::string output;

            // Read the output of the command
            while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
                output += buffer;
            }
            pclose(pipe);

            // Check for Arduino-specific attributes in the output
            std::regex vendorRegex(R"(ATTRS\{idVendor\}==\"2341\")");  // Arduino vendor ID
            std::regex productRegex(R"(ATTRS\{idProduct\}==\"0043\")"); // Arduino Uno product ID

            if (std::regex_search(output, vendorRegex) && std::regex_search(output, productRegex)) {
                detectedPort = portName;
                break;
            }
        }
    }

    return detectedPort;
}

// Initialize the serial port
int initializeSerialPort(const std::string& portName, int baudRate) {
    int serialPort = open(portName.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
    if (serialPort == -1) {
        std::cerr << "Error: Unable to open serial port " << portName << std::endl;
        return -1;
    }
    struct termios tty;
    if (tcgetattr(serialPort, &tty) != 0) {
        std::cerr << "Error: Unable to get terminal attributes" << std::endl;
        close(serialPort);
        return -1;
    }
    cfsetispeed(&tty, baudRate);
    cfsetospeed(&tty, baudRate);
    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;
    tty.c_iflag &= ~IGNBRK;
    tty.c_lflag = 0;
    tty.c_oflag = 0;
    tty.c_cc[VMIN] = 0;  // Allow non-blocking reads
    tty.c_cc[VTIME] = 1; // 0.1 second timeout
    tty.c_iflag &= ~(IXON | IXOFF | IXANY);
    tty.c_cflag |= (CLOCAL | CREAD);
    tty.c_cflag &= ~(PARENB | PARODD);
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CRTSCTS;
    if (tcsetattr(serialPort, TCSANOW, &tty) != 0) {
        std::cerr << "Error: Unable to set terminal attributes" << std::endl;
        close(serialPort);
        return -1;
    }
    return serialPort;
}

// Read data from the serial port line by line
std::string readFromSerialPort(int serialPort) {
    static std::string buffer; // Buffer to store partial data
    char ch;
    while (read(serialPort, &ch, 1) > 0) {
        buffer += ch;
        if (ch == '\n') { // When a newline is encountered
            std::string result = buffer;
            buffer.clear(); // Clear buffer for next line
            return result;  // Return the complete line
        }
    }
    return ""; // Return an empty string if no complete line is available
}

// Get the current timestamp
std::string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    std::time_t now_time = std::chrono::system_clock::to_time_t(now);
    std::tm* local_time = std::localtime(&now_time);
    std::ostringstream oss;
    oss << std::put_time(local_time, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

int main() {
    // Detect Arduino port
    std::string portName = detectArduinoPort();

    if (portName.empty()) {
        std::cerr << "No Arduino detected on /dev/ttyACM*" << std::endl;
        return -1;
    }

    std::cout << "Arduino detected on port: " << portName << std::endl;

    const int baudRate = B115200; // Match Arduino baud rate

    int serialPort = initializeSerialPort(portName, baudRate);
    if (serialPort == -1) {
        return -1;
    }

    std::ofstream outFile("arduino_data.csv", std::ios::app);
    if (!outFile.is_open()) {
        std::cerr << "Error: Unable to open file for writing" << std::endl;
        close(serialPort);
        return -1;
    }

    while (true) {
        std::string data = readFromSerialPort(serialPort);
        if (!data.empty()) {
            std::string timestamp = getCurrentTimestamp();
            std::cout << "[" << timestamp << "] " << data << std::endl;
            outFile << timestamp << ", " << data << std::endl;
            outFile.flush();
        }
    }

    outFile.close();
    close(serialPort);
    return 0;
}
