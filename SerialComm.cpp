#include <iostream>
#include <errno.h>
#include <string>
#include "SerialComm.h"

SerialComm::SerialComm(const char* device, unsigned long baud) : device(device), baud(baud), fd(-1), time(0){}
SerialComm::~SerialComm(){
	if(fd>=0){
		serialClose(fd);
	}
}

bool SerialComm::setup(){
	std::cout << "Raspberry startup!" << std::endl;
	if((fd = serialOpen(device, baud)) <0){
		std::cerr << "Unable to open Serial device: " << strerror(errno) << std::endl;
		return false;
	}
	if (wiringPiSetup()==-1){
		std::cerr << "Unable to start wiringPi: " << strerror(errno) << std::endl;
		return false;
	}
}

void saveToFile(const std::string& data, const int portNumber){
	namespace fs = std::filesystem;

	auto now = std::chrono::system_clock::now();
	std::time_t time = std::chrono::system_clock::to_time_t(now);

	std::ostringstream folderStream;
	folderStream << std::put_time(std::localtime(&time), "%Y-%m-%d");
	std::string folderName = folderStream.str();

	std::ostringstream filename_stream;
	filename_stream << std::p[ut_time(std::localtime(&time), "%Y%m%d_%H%M") << ".yaml";
	std::string filename = filename_stream.str();

	if(!fs.exists(folderName)){
		if(!fs::create_directory(folderName)){
			return;
		}
	}
	std::string filePath = folderName + "/" + fileName;

	std::ostringstream timestampStream;
	timestampStream << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
	auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
	timestampStream << "." << millis.count();
	std::string timestamp = timestampStream.str();

	std::ofstream fout(filePath, std::ios::app);
	if (!fout.is_open()){
		std::cerr << "Error opening file: " << filePath << std::endl;
		return;
	}

	fout << "timestamp: \"" << timestamp << "\"laser data: \"" << data << "\"" << std::endl;
	fout.close();
	}
}

void SerialComm::sendData(const char* data){ }

std::string SerialComm::str_receivedData(){
	int data;
	std::string str_data = "";
	int portNumber = 1;
	while (true){
		if(isDataAvailable()){
			data = serialGetchar(fd);
			if (data == -1){
				break;
			}
			else if (data == '\n'){
				auto now = std::chrono::system_clock::now();
				std::time_t time = std::chrono::system_clock::to_time_t(now);
				auto millis = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch())%1000;
				std::cout << std::put_time(&time), "Y-%m-%d %H:%M:%S") << "." << millis.count() << std::endl;
				saveTofile(str_data, portNumber);
				break;
			}
			else if (data != '\0'){
				str_data += static_cast<char>(data);
			}
		}
	}
	return str_data;
}

boll SerialComm:isDataAvailable(){
	return serialDataAvail(fd);
}
