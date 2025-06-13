#include <Wire.h>

// TSL2591 Constants (from library analysis)
#define TSL2591_ADDR (0x29)
#define TSL2591_COMMAND_BIT (0xA0)
#define TSL2591_WORD_BIT (0x20)

// Register addresses
#define TSL2591_REGISTER_ENABLE (0x00)
#define TSL2591_REGISTER_CONTROL (0x01)
#define TSL2591_REGISTER_DEVICE_ID (0x12)
#define TSL2591_REGISTER_CHAN0_LOW (0x14)
#define TSL2591_REGISTER_CHAN0_HIGH (0x15)
#define TSL2591_REGISTER_CHAN1_LOW (0x16)
#define TSL2591_REGISTER_CHAN1_HIGH (0x17)

// Control register values
#define TSL2591_ENABLE_POWEROFF (0x00)
#define TSL2591_ENABLE_POWERON (0x01)
#define TSL2591_ENABLE_AEN (0x02)
#define TSL2591_ENABLE_AIEN (0x10)
#define TSL2591_ENABLE_NPIEN (0x80)

// Gain settings
#define TSL2591_GAIN_LOW (0x00)   // 1x
#define TSL2591_GAIN_MED (0x10)   // 25x
#define TSL2591_GAIN_HIGH (0x20)  // 428x
#define TSL2591_GAIN_MAX (0x30)   // 9876x

// Integration time settings
#define TSL2591_INTEGRATIONTIME_100MS (0x00)
#define TSL2591_INTEGRATIONTIME_200MS (0x01)
#define TSL2591_INTEGRATIONTIME_300MS (0x02)
#define TSL2591_INTEGRATIONTIME_400MS (0x03)
#define TSL2591_INTEGRATIONTIME_500MS (0x04)
#define TSL2591_INTEGRATIONTIME_600MS (0x05)

// Channel definitions
#define TSL2591_VISIBLE (2)
#define TSL2591_INFRARED (1)
#define TSL2591_FULLSPECTRUM (0)

// Lux calculation constants
#define TSL2591_LUX_DF (408.0F)

// TSL2591 class replacement
class SimpleTSL2591 {
private:
    uint8_t _gain;
    uint8_t _integration;
    uint8_t _addr;
    bool _initialized;

    // I2C communication functions
    uint8_t read8(uint8_t reg) {
        Wire.beginTransmission(_addr);
        Wire.write(reg);
        Wire.endTransmission();
        Wire.requestFrom(_addr, (uint8_t)1);
        if (Wire.available()) {
            return Wire.read();
        }
        return 0;
    }

    uint16_t read16(uint8_t reg) {
        Wire.beginTransmission(_addr);
        Wire.write(reg);
        Wire.endTransmission();
        Wire.requestFrom(_addr, (uint8_t)2);
        if (Wire.available() >= 2) {
            uint8_t low = Wire.read();
            uint8_t high = Wire.read();
            return (uint16_t(high) << 8) | uint16_t(low);
        }
        return 0;
    }

    void write8(uint8_t reg, uint8_t value) {
        Wire.beginTransmission(_addr);
        Wire.write(reg);
        Wire.write(value);
        Wire.endTransmission();
    }

    void write8(uint8_t reg) {
        Wire.beginTransmission(_addr);
        Wire.write(reg);
        Wire.endTransmission();
    }

public:
    SimpleTSL2591(uint8_t addr = TSL2591_ADDR) {
        _addr = addr;
        _initialized = false;
        _integration = TSL2591_INTEGRATIONTIME_300MS;
        _gain = TSL2591_GAIN_MED;
    }

    bool begin() {
        Wire.begin();
        
        // Check device ID
        uint8_t id = read8(TSL2591_COMMAND_BIT | TSL2591_REGISTER_DEVICE_ID);
        if (id != 0x50) {
            return false;
        }

        _initialized = true;
        
        // Set default timing and gain
        setTiming(_integration);
        setGain(_gain);
        
        // Start in power down mode
        disable();
        
        return true;
    }

    void enable() {
        if (!_initialized) return;
        write8(TSL2591_COMMAND_BIT | TSL2591_REGISTER_ENABLE,
               TSL2591_ENABLE_POWERON | TSL2591_ENABLE_AEN | 
               TSL2591_ENABLE_AIEN | TSL2591_ENABLE_NPIEN);
    }

    void disable() {
        if (!_initialized) return;
        write8(TSL2591_COMMAND_BIT | TSL2591_REGISTER_ENABLE, 
               TSL2591_ENABLE_POWEROFF);
    }

    void setGain(uint8_t gain) {
        if (!_initialized) return;
        enable();
        _gain = gain;
        write8(TSL2591_COMMAND_BIT | TSL2591_REGISTER_CONTROL, 
               _integration | _gain);
        disable();
    }

    void setTiming(uint8_t integration) {
        if (!_initialized) return;
        enable();
        _integration = integration;
        write8(TSL2591_COMMAND_BIT | TSL2591_REGISTER_CONTROL, 
               _integration | _gain);
        disable();
    }

    uint8_t getGain() { return _gain; }
    uint8_t getTiming() { return _integration; }

    uint32_t getFullLuminosity() {
        if (!_initialized) return 0;

        enable();

        // Wait for integration time
        uint8_t delay_time = (_integration + 1) * 120;
        delay(delay_time);

        // Read channels (CH0 must be read before CH1)
        uint16_t ch0 = read16(TSL2591_COMMAND_BIT | TSL2591_REGISTER_CHAN0_LOW);
        uint16_t ch1 = read16(TSL2591_COMMAND_BIT | TSL2591_REGISTER_CHAN1_LOW);

        disable();

        return (uint32_t(ch1) << 16) | uint32_t(ch0);
    }

    uint16_t getLuminosity(uint8_t channel) {
        uint32_t x = getFullLuminosity();

        if (channel == TSL2591_FULLSPECTRUM) {
            return (x & 0xFFFF);
        } else if (channel == TSL2591_INFRARED) {
            return (x >> 16);
        } else if (channel == TSL2591_VISIBLE) {
            return ((x & 0xFFFF) - (x >> 16));
        }
        return 0;
    }

    float calculateLux(uint16_t ch0, uint16_t ch1) {
        // Check for overflow
        if ((ch0 == 0xFFFF) || (ch1 == 0xFFFF)) {
            return -1;
        }

        float atime, again;

        // Get integration time in ms
        switch (_integration) {
            case TSL2591_INTEGRATIONTIME_100MS: atime = 100.0F; break;
            case TSL2591_INTEGRATIONTIME_200MS: atime = 200.0F; break;
            case TSL2591_INTEGRATIONTIME_300MS: atime = 300.0F; break;
            case TSL2591_INTEGRATIONTIME_400MS: atime = 400.0F; break;
            case TSL2591_INTEGRATIONTIME_500MS: atime = 500.0F; break;
            case TSL2591_INTEGRATIONTIME_600MS: atime = 600.0F; break;
            default: atime = 100.0F; break;
        }

        // Get gain multiplier
        switch (_integration) {
            case TSL2591_GAIN_LOW:  again = 1.0F; break;
            case TSL2591_GAIN_MED:  again = 25.0F; break;
            case TSL2591_GAIN_HIGH: again = 428.0F; break;
            case TSL2591_GAIN_MAX:  again = 9876.0F; break;
            default: again = 1.0F; break;
        }

        // Calculate CPL (Counts Per Lux)
        float cpl = (atime * again) / TSL2591_LUX_DF;

        // Calculate lux using AMS algorithm
        float lux = (((float)ch0 - (float)ch1)) * (1.0F - ((float)ch1 / (float)ch0)) / cpl;

        return lux;
    }
};

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

// Global variables
SimpleTSL2591 tsl;
LightSensorData lastLightData = {0, 0, 0, 0, 0, 0, 0, 0};

void setup() {
    Serial.begin(9600);
    Serial2.begin(115200);
    
    if (!tsl.begin()) {
        Serial.println("TSL2591 sensor not found!");
        while(1); // Stop here if sensor not found
    }
    
    configureSensor();
}

void configureSensor() {
    tsl.setGain(TSL2591_GAIN_MED);      // medium gain (25x)
    tsl.setTiming(TSL2591_INTEGRATIONTIME_300MS); // 300ms
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

void loop() {
    // 레이저 센서 데이터 계속 읽기 및 출력 (최우선 처리)
    if (Serial2.available() >= 9) {  // 9바이트 데이터 수신 확인
        // 패킷 시작 확인
        if (Serial2.read() == 0x59 && Serial2.read() == 0x59) {
            int distance = Serial2.read() + (Serial2.read() << 8);  // 거리
            int strength = Serial2.read() + (Serial2.read() << 8);
            uint8_t temp_low = Serial2.read();   // buf[6] 해당
            uint8_t temp_high = Serial2.read();  // buf[7] 해당
            float temperature = ((temp_high << 8) | temp_low) / 80.0;
            
            // 데이터 검증: 합리적인 범위 내의 값만 출력
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