#include <iostream>
#include <thread>
#include <atomic>
#include <termios.h>
#include <unistd.h>
#include <string>
#include "SerialComm.h"

char getKeyPress(){
	struct termios oldt, newt;
	char ch;
	tcgetattr(STDIN_FILENO, &oldt);
	newt = oldt;
	newt.c_lflag &= ~(ICANON | ECHO);
	tcsetattr(STDIN_FILENO, TCSANOW, &newt);
	ch = getchar();
	tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
	return ch;
}

int main(){
	SerialComm SerialComm1("/dev/ttyACM0", 9600);
	SerialComm SerialComm2("/dev/ttyACM1", 9600);
	SerialComm SerialComm3("/dev/ttyACM2", 9600);
	SerialComm SerialComm4("/dev/ttyACM3", 9600);
	if (!SerialComm1.setup()) || !SerialComm2.setup()) || !SerialComm3.setup()|| !SerialComm4.setup()){
		std::cout<<"setup_error" << std::endl;
		return 0;
	}
	std::atomic<bool> paused(false);
	bool running = true;
	std::string labelInput;
	std::thread inputThread([&](){
		while (running){
			char key = getKeyPress();
			if(key == 's' || key == 'S'){
				paused = true;
			}
			else if (key == 'p' || key == 'P'){
				paused = false;
			}
			else if (key == 'l' || key == 'L'){
				std::getline(std::cin, labelInput);
			}
		}
	});

	while(running){
		if(!paused){
			std::string Serial1_data = SerialComm1.str_receiveData();
			std::string Serial2_data = SerialComm2.str_receiveData();
			std::string Serial3_data = SerialComm3.str_receiveData();
			std::string Serial4_data = SerialComm4.str_receiveData();
			if(!Serial1_data.empty()){
				std::cout << "Received Arduino[1]_(Load: "<<labelInput << ") data: " << Serial1_data << std::endl;
				SerialComm1.saveToFile(Serial1_data, 1, labelInput);
			}
			if(!Serial2_data.empty()){
				std::cout << "Received Arduino[2]_(Load: "<<labelInput << ") data: " << Serial2_data << std::endl;
				SerialComm2.saveToFile(Serial2_data, 2, labelInput);
			}
			if(!Serial3_data.empty()){
				std::cout << "Received Arduino[3]_(Load: "<<labelInput << ") data: " << Serial3_data << std::endl;
				SerialComm3.saveToFile(Serial3_data, 3, labelInput);
			}
			if(!Serial4_data.empty()){
				std::cout << "Received Arduino[4]_(Load: "<<labelInput << ") data: " << Serial4_data << std::endl;
				SerialComm4.saveToFile(Serial4_data, 4, labelInput);
		}
		else{
			std::this_thread::sleep_for(std::chrono::milliseconds(100));
		}
	}
	inputThread.join();
	return 0;
}
