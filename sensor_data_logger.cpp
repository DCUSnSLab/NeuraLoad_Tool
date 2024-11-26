#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <ctime>
#include <thread>
#include <chrono>
#include <cstdlib>

// Function to generate mock sensor data
std::string generateSensorData() {
    std::ostringstream data;
    int mockValue = rand() % 100;
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

int main() {
    const std::string filename = "sensor_data.csv";

    try {
        while (true) {
            // Simulate sensor data generation
            std::string sensorData = generateSensorData();
            std::cout << "Generated: " << sensorData << std::endl;
            
            // Save to file with timestamp
            saveDataToFile(sensorData, filename);

            // Wait for 1 second before the next iteration
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    return 0;
}