#include "dataCheckTool.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QFile>
#include <QTextStream>
#include <QMessageBox>
#include <yaml-cpp/yaml.h>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent), isUpdating(true) {
    // UI 설정
    QWidget *centralWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);

    // Device-specific 데이터 설정
    QHBoxLayout *deviceLayout = new QHBoxLayout();
    deviceData1 = new QListWidget(this);
    deviceData2 = new QListWidget(this);
    deviceData3 = new QListWidget(this);
    deviceData4 = new QListWidget(this);
    deviceData5 = new QListWidget(this);

    deviceLayout->addWidget(new QLabel("Device 1", this));
    deviceLayout->addWidget(deviceData1);
    deviceLayout->addWidget(new QLabel("Device 2", this));
    deviceLayout->addWidget(deviceData2);
    deviceLayout->addWidget(new QLabel("Device 3", this));
    deviceLayout->addWidget(deviceData3);
    deviceLayout->addWidget(new QLabel("Device 4", this));
    deviceLayout->addWidget(deviceData4);
    deviceLayout->addWidget(new QLabel("Device 5", this));
    deviceLayout->addWidget(deviceData5);

    // Bottom section: General real-time data
    QLabel *generalDataLabel = new QLabel("General Real-time Data", this);
    generalDataList = new QListWidget(this);

    // Right panel: Controls
    QVBoxLayout *controlLayout = new QVBoxLayout();
    QLabel *label = new QLabel("Enter Load Label:", this);
    loadInput = new QLineEdit(this);
    QPushButton *applyLoadButton = new QPushButton("Apply Load Label", this);

    stopResumeButton = new QPushButton("Stop/Resume", this);
    extractYamlButton = new QPushButton("Extract YAML", this);
    saveDataButton = new QPushButton("Save Data", this);
    trackChangesButton = new QPushButton("Track Changes", this);

    controlLayout->addWidget(label);
    controlLayout->addWidget(loadInput);
    controlLayout->addWidget(applyLoadButton);
    controlLayout->addWidget(stopResumeButton);
    controlLayout->addWidget(extractYamlButton);
    controlLayout->addWidget(saveDataButton);
    controlLayout->addWidget(trackChangesButton);

    mainLayout->addLayout(deviceLayout);
    mainLayout->addWidget(generalDataLabel);
    mainLayout->addWidget(generalDataList);
    mainLayout->addLayout(controlLayout);

    setCentralWidget(centralWidget);

    // SerialComm 객체 초기화
    serialComm = new SerialComm(this);
    
    // Connect signals to slots
    connect(applyLoadButton, &QPushButton::clicked, this, &MainWindow::applyLoadLabel);

    // Start the data collection
    startRealTimeData();
}

MainWindow::~MainWindow() {
    delete serialComm;  // 리소스 해제
}

void MainWindow::applyLoadLabel() {
    QString loadLabel = loadInput->text();
    if (!loadLabel.isEmpty() && generalDataList->currentItem()) {
        generalDataList->currentItem()->setText(
            generalDataList->currentItem()->text() + " (" + loadLabel + ")");
    }
}

void MainWindow::startRealTimeData() {
    QTimer *timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, [this]() {
        static int count = 1;

        // SerialComm 객체를 통해 데이터 받기
        QString sensorData1 = serialComm->getDataFromDevice(1);
        QString sensorData2 = serialComm->getDataFromDevice(2);
        QString sensorData3 = serialComm->getDataFromDevice(3);
        QString sensorData4 = serialComm->getDataFromDevice(4);
        QString sensorData5 = serialComm->getDataFromDevice(5);

        // Device-specific data 업데이트
        deviceData1->addItem("Device 1 - Data: " + sensorData1);
        deviceData2->addItem("Device 2 - Data: " + sensorData2);
        deviceData3->addItem("Device 3 - Data: " + sensorData3);
        deviceData4->addItem("Device 4 - Data: " + sensorData4);
        deviceData5->addItem("Device 5 - Data: " + sensorData5);

        // General real-time data 업데이트
        generalDataList->addItem("General Data " + QString::number(count));
        ++count;
    });

    timer->start(1000); // 1초마다 데이터 갱신
}
