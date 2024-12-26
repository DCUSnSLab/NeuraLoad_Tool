#ifndef SERIALCOMM_H
#define SERIALCOMM_H
#include <wiringPi.h>
#include <wiringSerial.h>
#include <string>
class SerialComm{
	public:
		SerialComm(const char* device, unsigned long baud);
		~SerialComm();
		bool setup();
		void sendData(const char* data);
		int receiveData();
		std::string str_receiveData();
		bool isDataAvailable();
		void saveToFile(const std::string& data, const int portNumber, const std::string& label);
		void flushBuffer();
//		std::string applyLabel(const std::string& data, const std::string& label);
	private:
		int fd; //file discriptor
		unsigned long baud;
		const char* device; // collect_device(arduino) route
		unsigned long time;
};

#endif // SERIALCOMM_H

