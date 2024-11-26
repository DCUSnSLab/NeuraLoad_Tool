#include <iostream>
#include <fstream>
#include <string>
#include <chrono>
#include <thread>
#include <ctime>
#include <iomanip>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <sstream>

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
    tty.c_cc[VMIN] = 1;
    tty.c_cc[VTIME] = 1;
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
    std::string result;
    char buffer;
    while (read(serialPort, &buffer, 1) > 0) {
        if (buffer == '\n') {
            break;
        }
        result += buffer;
    }
    return result;
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
    const std::string portName = "/dev/ttyACM0";
    const int baudRate = B9600;

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
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    outFile.close();
    close(serialPort);
    return 0;
}
