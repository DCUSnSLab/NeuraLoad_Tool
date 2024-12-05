#include "dataCheckTool.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QLabel>
#include <QTimer>

MainWindow::MainWindow(QWidget *parent) : QMainWindow(parent) {
    // Main widget and layout
    QWidget *centralWidget = new QWidget(this);
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);

    // Top section: Device-specific data
    QHBoxLayout *deviceLayout = new QHBoxLayout();
    QLabel *deviceLabel1 = new QLabel("Device 1", this);
    deviceData1 = new QListWidget(this);
    QLabel *deviceLabel2 = new QLabel("Device 2", this);
    deviceData2 = new QListWidget(this);
    QLabel *deviceLabel3 = new QLabel("Device 3", this);
    deviceData3 = new QListWidget(this);
    QLabel *deviceLabel4 = new QLabel("Device 4", this);
    deviceData4 = new QListWidget(this);
    QLabel *deviceLabel5 = new QLabel("Device 5", this);
    deviceData5 = new QListWidget(this);

    deviceLayout->addWidget(deviceLabel1);
    deviceLayout->addWidget(deviceData1);
    deviceLayout->addWidget(deviceLabel2);
    deviceLayout->addWidget(deviceData2);
    deviceLayout->addWidget(deviceLabel3);
    deviceLayout->addWidget(deviceData3);
    deviceLayout->addWidget(deviceLabel4);
    deviceLayout->addWidget(deviceData4);
    deviceLayout->addWidget(deviceLabel5);
    deviceLayout->addWidget(deviceData5);

    // Bottom section: General real-time data
    QLabel *generalDataLabel = new QLabel("General Real-time Data", this);
    generalDataList = new QListWidget(this);

    // Right panel: Controls
    QVBoxLayout *controlLayout = new QVBoxLayout();
    QLabel *label = new QLabel("Enter Load Label:", this);
    loadInput = new QLineEdit(this);
    QPushButton *applyLoadButton = new QPushButton("Apply Load Label", this);

    QPushButton *stopResumeButton = new QPushButton("Stop/Resume", this);
    QPushButton *extractYamlButton = new QPushButton("Extract YAML", this);
    QPushButton *saveDataButton = new QPushButton("Save Data", this);
    QPushButton *trackChangesButton = new QPushButton("Track Changes", this);

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

    // Connect signals to slots
    connect(applyLoadButton, &QPushButton::clicked, this, &MainWindow::applyLoadLabel);

    // Simulate real-time data
    startRealTimeData();
}

MainWindow::~MainWindow() {}

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

        // Update device-specific data
        deviceData1->addItem("Device 1 - Data " + QString::number(count));
        deviceData2->addItem("Device 2 - Data " + QString::number(count));
        deviceData3->addItem("Device 3 - Data " + QString::number(count));
        deviceData4->addItem("Device 4 - Data " + QString::number(count));
        deviceData5->addItem("Device 5 - Data " + QString::number(count));

        // Update general real-time data
        generalDataList->addItem("General Data " + QString::number(count));
        ++count;
    });

    timer->start(1000); // Update every second
}
