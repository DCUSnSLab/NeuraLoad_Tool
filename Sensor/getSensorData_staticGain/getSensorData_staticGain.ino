#include <Wire.h>
#include <Adafruit_Sensor.h>
#include "Adafruit_TSL2591.h"

Adafruit_TSL2591 tsl = Adafruit_TSL2591(2591);

// 조도 센서 데이터 구조체
struct LightSensorData {
    float lux;
    float gainMultiplier;
    float integrationTime;
    float cpl;
    uint16_t visible;
    uint16_t ch0;
    uint16_t ch1;
    uint32_t fullLuminosity;
};

// 이전 조도 데이터 저장용 전역 변수
LightSensorData lastLightData = {0, 0, 0, 0, 0, 0, 0, 0};

void setup() {
    Serial.begin(9600);
    Serial2.begin(115200);
    configureSensor();
}

void configureSensor() {
  	tsl.setGain(TSL2591_GAIN_MED); // medium gain (25x)
	tsl.setTiming(TSL2591_INTEGRATIONTIME_300MS); // 300ms
}

void loop() {
    // 레이저 센서 데이터 계속 읽기 및 출력 (최우선 처리)
    if (Serial2.available() >= 9) {  // 9바이트 데이터 수신 확인
        // 패킷 시작 확인
        if (Serial2.read() == 0x59 && Serial2.read() == 0x59) {
            int distance = Serial2.read() + (Serial2.read() << 8);  // 거리
            int strength = Serial2.read() + (Serial2.read() << 8);
            uint8_t temp_low = Serial2.read();   // buf[6] 해당
            uint8_t temp_high = Serial2.read();  // buf[7] 해당
            float temperature = ((temp_high << 8) | temp_low) / 80;
            
            // // 데이터 검증: 합리적인 범위 내의 값만 출력
            if (distance >= 0 && distance <= 12000 && // 거리: 0~12m
                strength >= 0 && strength <= 32767 && // 강도: 0~32767
                temperature >= -40 && temperature <= 100) { // 온도: -40~100
                
                // 레이저 센서 데이터와 이전 조도 센서 데이터 함께 출력
				Serial.print(distance);
				Serial.print(',');
				Serial.print(strength);
				Serial.print(',');
				Serial.print(temperature);
				Serial.print(',');
				Serial.print(lastLightData.lux);
				Serial.print(',');
				Serial.print(lastLightData.gainMultiplier);
				Serial.print(',');
				Serial.print(lastLightData.integrationTime);
				Serial.print(',');
				Serial.print(lastLightData.cpl);
				Serial.print(',');
				Serial.print(lastLightData.visible);
				Serial.print(',');
				Serial.print(lastLightData.ch0);
				Serial.print(',');
				Serial.print(lastLightData.ch1);
				Serial.print(',');
				Serial.println(lastLightData.fullLuminosity);
            }
            else {
                // 남은 바이트 읽어서 버퍼 클리어
                while (Serial2.available() > 0) {
                    Serial2.read();
                }
            }
        }
        return; // 레이저 데이터 처리 후 즉시 리턴하여 연속 처리 가능
    }

    // 조도 센서 데이터 수집 및 업데이트 (레이저 데이터가 없을 때만 처리)
    unsigned long currentTime = millis();
    static unsigned long lastLightSensorTime = 0;
    static unsigned long lightDataStartTime = 0;
    static bool isCollectingLightData = false;
    
    // 조도 센서 데이터 수집 시작 (1초마다)
    if (currentTime - lastLightSensorTime >= 1000 && !isCollectingLightData) {
        isCollectingLightData = true;
        lightDataStartTime = currentTime;
    }
    
    // 조도 센서 데이터 수집 중 (작은 단위로 나누어 처리)
    if (isCollectingLightData) {
        unsigned long elapsed = currentTime - lightDataStartTime;
        
        if (elapsed >= 50) { // 50ms 후 데이터 수집 완료
            // 센서 데이터 수집하여 구조체에 저장
            uint32_t fullLuminosity = tsl.getFullLuminosity();
            uint16_t ch0 = fullLuminosity & 0xFFFF;
            uint16_t ch1 = fullLuminosity >> 16;
            uint16_t visible = tsl.getLuminosity(TSL2591_VISIBLE);
            float lux = tsl.calculateLux(ch0, ch1);
            float cpl = calculateCPL();
            float gainMultiplier = getGainMultiplier();
            float integrationTime = (tsl.getTiming() + 1) * 100.0F;
            
            // 구조체에 새로운 데이터 저장
            lastLightData.lux = lux;
            lastLightData.gainMultiplier = gainMultiplier;
            lastLightData.integrationTime = integrationTime;
            lastLightData.cpl = cpl;
            lastLightData.visible = visible;
            lastLightData.ch0 = ch0;
            lastLightData.ch1 = ch1;
            lastLightData.fullLuminosity = fullLuminosity;
            
            lastLightSensorTime = currentTime;
            isCollectingLightData = false;
        }
    }
}

float calculateCPL() {
    float atime, again;

    switch (tsl.getTiming()) {
        case TSL2591_INTEGRATIONTIME_100MS: atime = 100.0F; break;
        case TSL2591_INTEGRATIONTIME_200MS: atime = 200.0F; break;
        case TSL2591_INTEGRATIONTIME_300MS: atime = 300.0F; break;
        case TSL2591_INTEGRATIONTIME_400MS: atime = 400.0F; break;
        case TSL2591_INTEGRATIONTIME_500MS: atime = 500.0F; break;
        case TSL2591_INTEGRATIONTIME_600MS: atime = 600.0F; break;
        default: atime = 100.0F; break;
    }

    switch (tsl.getGain()) {
        case TSL2591_GAIN_LOW:  again = 1.0F; break;
        case TSL2591_GAIN_MED:  again = 25.0F; break;
        case TSL2591_GAIN_HIGH: again = 428.0F; break;
        case TSL2591_GAIN_MAX:  again = 9876.0F; break;
        default: again = 1.0F; break;
    }

    return (atime * again) / 408.0F;
}

float getGainMultiplier() {
    switch (tsl.getGain()) {
        case TSL2591_GAIN_LOW:  return 1.0F;
        case TSL2591_GAIN_MED:  return 25.0F;
        case TSL2591_GAIN_HIGH: return 428.0F;
        case TSL2591_GAIN_MAX:  return 9876.0F;
        default: return 1.0F;
    }
}