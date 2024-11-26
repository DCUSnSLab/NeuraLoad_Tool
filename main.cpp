#include <iostream>
#include <string>
#include <atomic>
#include <termios.h>
#include <unistd.h>
#include "SerialComm.h"

char getKeyPress(){
	struct termios oldt, newt;
	char ch;
	tcgetattr(STDIN_FILNO, &oldt);
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

	if (!SerialComm1.setup() || !SerialComm2.setup() || !SerialComm3.setup() || !SerialComm4.setup()){
		return 0;
	}
	std::atomic<bool>paused(false);
	bool running = true;
	std::thread inputThread([&](){
		while (running){
			char key = getKeyPress();
			if (key == 's' || key == 'S'){
				paused = true;
				}
				else if (key == 'r' || key == 'R'){
					pased = false;
				}
			}
		}
	});
	while(running){
		if(!paused){
			std::string Serial1_data = SerialComm1.str_receivedData();
			std::string Serial2_data = SerialComm2.str_receivedData();
			std::string Serial3_data = SerialComm3.str_receivedData();
			std::string Serial4_data = SerialComm4.str_receivedData();
			if (!Serial1_data.empty()){
				std::cout << "Recieved Arduino[1] data : " << Serial1_data << std::endl;
				SerialComm1.saveToFile(Serial1_data, 1);
			}
			if (!Serial2_data.empty()){
				std::cout << "Recieved Arduino[2] data : " << Serial1_data << std::endl;
				SerialComm2.saveToFile(Serial2_data, 2);
			}
			if (!Serial3_data.empty()){
				std::cout << "Recieved Arduino[3] data : " << Serial1_data << std::endl;
				SerialComm3.saveToFile(Serial3_data, 3);
			}
			if (!Serial4_data.empty()){
				std::cout << "Recieved Arduino[4] data : " << Serial1_data << std::endl;
				SerialComm4.saveToFile(Serial4_data, 4);
			}
		}
		else{
			std::this_thread::sleep_for(std::chrono::milliseconds(100));
		}
	}
	inputThread.join();
	return 0;
}



