#ifndef DATACHECKTOOL_H
#define DATACHECKTOOL_H

#include <QMainWindow>
#include <QListWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QTimer>
#include "SerialComm.h"  // 센서 데이터 받는 클래스를 포함

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void applyLoadLabel();        // Load label을 적용
    void startRealTimeData();     // 실시간 데이터 받기
    void stopOrResumeUpdates();   // 데이터 업데이트 중지/재개
    void saveDataToFile();        // 데이터를 파일로 저장
    void extractToYaml();         // 데이터를 YAML로 추출
    void trackDataChanges();      // 데이터 변화 추적

private:
    // Device-specific data
    QListWidget *deviceData1;
    QListWidget *deviceData2;
    QListWidget *deviceData3;
    QListWidget *deviceData4;
    QListWidget *deviceData5;

    // General real-time data
    QListWidget *generalDataList;

    // Load label input
    QLineEdit *loadInput;

    // 추가된 멤버들
    QPushButton *stopResumeButton;
    QPushButton *extractYamlButton;
    QPushButton *saveDataButton;
    QPushButton *trackChangesButton;

    QTimer *dataUpdateTimer;      // 실시간 데이터 업데이트 타이머
    SerialComm *serialComm;       // 센서 데이터 통신 객체
    bool isUpdating;              // 데이터 업데이트 상태
};

#endif // DATACHECKTOOL_H
