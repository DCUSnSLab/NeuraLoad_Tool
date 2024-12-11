#include "dataCheckTool.h"
#include "SerialComm.h"  // 센서 데이터 통신 클래스
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QWidget>
#include <QTimer>
#include <QListWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QFile>
#include <QTextStream>
#include <QMessageBox>
#include <QDebug>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), isUpdating(false), serialComm(new SerialComm(this))
{
    // 메인 위젯과 레이아웃 설정
    QWidget *centralWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);
    QHBoxLayout *buttonLayout = new QHBoxLayout();

    // 리스트 위젯 초기화
    deviceData1 = new QListWidget(this);
    deviceData2 = new QListWidget(this);
    deviceData3 = new QListWidget(this);
    deviceData4 = new QListWidget(this);
    deviceData5 = new QListWidget(this);
    generalDataList = new QListWidget(this);

    // 라인 입력과 버튼 초기화
    loadInput = new QLineEdit(this);
    stopResumeButton = new QPushButton("Stop/Resume", this);
    extractYamlButton = new QPushButton("Extract YAML", this);
    saveDataButton = new QPushButton("Save Data", this);
    trackChangesButton = new QPushButton("Track Changes", this);

    // 버튼 레이아웃 구성
    buttonLayout->addWidget(stopResumeButton);
    buttonLayout->addWidget(extractYamlButton);
    buttonLayout->addWidget(saveDataButton);
    buttonLayout->addWidget(trackChangesButton);

    // 메인 레이아웃 구성
    mainLayout->addWidget(loadInput);
    mainLayout->addWidget(deviceData1);
    mainLayout->addWidget(deviceData2);
    mainLayout->addWidget(deviceData3);
    mainLayout->addWidget(deviceData4);
    mainLayout->addWidget(deviceData5);
    mainLayout->addWidget(generalDataList);
    mainLayout->addLayout(buttonLayout);

    // 메인 위젯 설정
    setCentralWidget(centralWidget);

    // 타이머 초기화
    dataUpdateTimer = new QTimer(this);

    // 시그널과 슬롯 연결
    connect(stopResumeButton, &QPushButton::clicked, this, &MainWindow::stopOrResumeUpdates);
    connect(extractYamlButton, &QPushButton::clicked, this, &MainWindow::extractToYaml);
    connect(saveDataButton, &QPushButton::clicked, this, &MainWindow::saveDataToFile);
    connect(trackChangesButton, &QPushButton::clicked, this, &MainWindow::trackDataChanges);
}

MainWindow::~MainWindow() {
    delete serialComm;
}

void MainWindow::applyLoadLabel() {
    QString label = loadInput->text();
    if (!label.isEmpty()) {
        generalDataList->addItem("Load Label: " + label);
    } else {
        generalDataList->addItem("Load Label: (Nan)");
    }
}

void MainWindow::startRealTimeData() {
    if (!dataUpdateTimer->isActive()) {
        connect(dataUpdateTimer, &QTimer::timeout, this, [this]() {
            QString data = serialComm->readData();
            generalDataList->addItem(data);
        });
        dataUpdateTimer->start(1000);  // 1초 간격
        isUpdating = true;
    }
}

void MainWindow::stopOrResumeUpdates() {
    if (isUpdating) {
        dataUpdateTimer->stop();
        isUpdating = false;
    } else {
        dataUpdateTimer->start(1000);  // 다시 시작
        isUpdating = true;
    }
}

void MainWindow::saveDataToFile() {
    QFile file("output.txt");
    if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&file);
        for (int i = 0; i < generalDataList->count(); ++i) {
            out << generalDataList->item(i)->text() << "\n";
        }
        file.close();
        QMessageBox::information(this, "Save Data", "Data saved to output.txt");
    } else {
        QMessageBox::critical(this, "Save Data", "Failed to save data.");
    }
}

void MainWindow::extractToYaml() {
    QFile file("output.yaml");
    if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&file);
        out << "general_data:\n";
        for (int i = 0; i < generalDataList->count(); ++i) {
            out << "  - " << generalDataList->item(i)->text() << "\n";
        }
        file.close();
        QMessageBox::information(this, "Extract YAML", "Data saved to output.yaml");
    } else {
        QMessageBox::critical(this, "Extract YAML", "Failed to extract YAML.");
    }
}

void MainWindow::trackDataChanges() {
    // 간단히 변화된 데이터를 시뮬레이션하는 예제
    for (int i = 0; i < generalDataList->count(); ++i) {
        QString originalText = generalDataList->item(i)->text();
        QString updatedText = originalText + " [Updated]";
        generalDataList->item(i)->setText(updatedText);
    }
    QMessageBox::information(this, "Track Changes", "Data changes tracked and updated.");
}
