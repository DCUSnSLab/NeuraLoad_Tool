ifndef SERIALCOMM_H;
define SERIALCOMM_H;
#include <wiringPi.h>
#include <wiringSerial.h>
#include <string>

class SerialComm{
public:
	SerialComm(const char* device, unsigned long baud);
	~SerialComm();
	bool setup();
	void saveToFile(const std::string& data, const int portNumber);
	void setData(const char* data);
	std::string str_receivedData();
	bool isDatavailable();
private:
	int fd;
	unsigned long baud;
	const char* device;
	unsigned long time;
};
#endif
