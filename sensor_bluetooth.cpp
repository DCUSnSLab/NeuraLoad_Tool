#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <ctime>
#include <thread>
#include <chrono>
#include <cstdlib>
#include <unistd.h>
#include <sys/socket.h>
#include <bluetooth/bluetooth.h>
#include <bluetooth/rfcomm.h>

// Function to generate mock sensor data
std::string generateSensorData() {
    std::ostringstream data;
    int mockValue = rand() % 100; // Generate random value between 0-99
    data << "Sensor Value: " << mockValue;
    return data.str();
}

// Function to get current timestamp as a string
std::string getTimestamp() {
    auto now = std::time(nullptr);
    char buffer[100];
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
    return std::string(buffer);
}

// Function to save data with timestamp to a file
void saveDataToFile(const std::string& data, const std::string& filename) {
    std::ofstream file(filename, std::ios::app);
    if (file.is_open()) {
        file << getTimestamp() << ", " << data << "\n";
        file.close();
    } else {
        std::cerr << "Failed to open file: " << filename << std::endl;
    }
}

// Function to set up BlueTooth communication
int setupBluetoothServer() {
    struct sockaddr_rc loc_addr = { 0 }, rem_addr = { 0 };
    int server_sock, client_sock;
    socklen_t opt = sizeof(rem_addr);

    // Create socket
    server_sock = socket(AF_BLUETOOTH, SOCK_STREAM, BTPROTO_RFCOMM);
    if (server_sock == -1) {
        std::cerr << "Failed to create Bluetooth socket." << std::endl;
        return -1;
    }

    // Bind socket to the RFCOMM channel 1
    loc_addr.rc_family = AF_BLUETOOTH;
    bdaddr_t any_addr = *BDADDR_ANY;
    loc_addr.rc_bdaddr = any_addr;
    loc_addr.rc_channel = (uint8_t)1;
    if (bind(server_sock, (struct sockaddr *)&loc_addr, sizeof(loc_addr)) == -1) {
        std::cerr << "Failed to bind Bluetooth socket." << std::endl;
        close(server_sock);
        return -1;
    }

    // Listen for incoming connections
    if (listen(server_sock, 1) == -1) {
        std::cerr << "Failed to listen on Bluetooth socket." << std::endl;
        close(server_sock);
        return -1;
    }

    std::cout << "Waiting for Bluetooth connection..." << std::endl;

    // Accept a connection
    client_sock = accept(server_sock, (struct sockaddr *)&rem_addr, &opt);
    if (client_sock == -1) {
        std::cerr << "Failed to accept Bluetooth connection." << std::endl;
        close(server_sock);
        return -1;
    }

    char client_address[18] = { 0 };
    ba2str(&rem_addr.rc_bdaddr, client_address);
    std::cout << "Connected to " << client_address << std::endl;

    return client_sock;
}

int main() {
    const std::string filename = "sensor_data.csv";
    int client_sock = setupBluetoothServer();

    if (client_sock == -1) {
        return -1;
    }

    try {
        while (true) {
            // Simulate sensor data generation
            std::string sensorData = generateSensorData();
            std::cout << "Generated: " << sensorData << std::endl;

            // Save to file with timestamp
            saveDataToFile(sensorData, filename);

            // Send data via Bluetooth
            int bytes_sent = send(client_sock, sensorData.c_str(), sensorData.length(), 0);
            if (bytes_sent == -1) {
                std::cerr << "Failed to send data via Bluetooth." << std::endl;
                break;
            }

            std::cout << "Sent via Bluetooth: " << sensorData << std::endl;

            // Wait for 1 second before the next iteration
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    close(client_sock);
    return 0;
}