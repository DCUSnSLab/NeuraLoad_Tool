#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QFile>
#include <QTextStream>
#include <QDateTime>
#include <QFileDialog>
#include <QMessageBox>
#include <QDir>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    // Initialize serial communication
    serialComm = new SerialComm(this);

    // Connect buttons to their respective slots
    connect(ui->startButton, &QPushButton::clicked, this, &MainWindow::startRealTimeData);
    connect(ui->stopButton, &QPushButton::clicked, this, &MainWindow::stopRealTimeData);
    connect(ui->saveDataButton, &QPushButton::clicked, this, &MainWindow::saveDataToFile);
    connect(ui->extractYamlButton, &QPushButton::clicked, this, &MainWindow::extractToYaml);
    connect(ui->trackChangesButton, &QPushButton::clicked, this, &MainWindow::trackDataChanges);

    // Initialize file list widget
    loadSavedFiles();
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::startRealTimeData()
{
    // Start generating real-time data
    dataTimer = new QTimer(this);
    connect(dataTimer, &QTimer::timeout, this, &MainWindow::updateRealTimeData);
    dataTimer->start(1000); // Update every second
}

void MainWindow::stopRealTimeData()
{
    if (dataTimer) {
        dataTimer->stop();
        delete dataTimer;
        dataTimer = nullptr;
    }
}

void MainWindow::updateRealTimeData()
{
    static int count = 0;
    count++;

    // Simulated data update
    ui->deviceData1->addItem("Device 1 - Data " + QString::number(count));
    ui->deviceData2->addItem("Device 2 - Data " + QString::number(count));
    ui->deviceData3->addItem("Device 3 - Data " + QString::number(count));
    ui->deviceData4->addItem("Device 4 - Data " + QString::number(count));
    ui->deviceData5->addItem("Device 5 - Data " + QString::number(count));

    applyLoadLabel(ui->deviceData1);
    applyLoadLabel(ui->deviceData2);
    applyLoadLabel(ui->deviceData3);
    applyLoadLabel(ui->deviceData4);
    applyLoadLabel(ui->deviceData5);
}

void MainWindow::applyLoadLabel(QListWidget *deviceData)
{
    if (deviceData->count() > 0) {
        QListWidgetItem *lastItem = deviceData->item(deviceData->count() - 1);
        QString dataText = lastItem->text();

        // Example processing to append load label
        dataText += " (Nan)";
        lastItem->setText(dataText);
    }
}

void MainWindow::saveDataToFile()
{
    QString timestamp = QDateTime::currentDateTime().toString("yyyyMMdd_HH");
    QString fileName = timestamp + ".txt";

    QFile file(fileName);
    if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&file);

        // Save all data from device lists
        out << "Device 1:\n";
        for (int i = 0; i < ui->deviceData1->count(); ++i)
            out << ui->deviceData1->item(i)->text() << "\n";

        out << "Device 2:\n";
        for (int i = 0; i < ui->deviceData2->count(); ++i)
            out << ui->deviceData2->item(i)->text() << "\n";

        out << "Device 3:\n";
        for (int i = 0; i < ui->deviceData3->count(); ++i)
            out << ui->deviceData3->item(i)->text() << "\n";

        out << "Device 4:\n";
        for (int i = 0; i < ui->deviceData4->count(); ++i)
            out << ui->deviceData4->item(i)->text() << "\n";

        out << "Device 5:\n";
        for (int i = 0; i < ui->deviceData5->count(); ++i)
            out << ui->deviceData5->item(i)->text() << "\n";

        file.close();

        // Reload file list in UI
        loadSavedFiles();
    }
}

void MainWindow::loadSavedFiles()
{
    QDir dir;
    QStringList files = dir.entryList(QStringList("*.txt"), QDir::Files);
    ui->fileListWidget->clear();
    ui->fileListWidget->addItems(files);
}

void MainWindow::extractToYaml()
{
    QListWidgetItem *selectedItem = ui->fileListWidget->currentItem();
    if (!selectedItem) {
        QMessageBox::warning(this, "No File Selected", "Please select a file to extract to YAML.");
        return;
    }

    QString fileName = selectedItem->text();
    QFile inputFile(fileName);
    if (!inputFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QMessageBox::critical(this, "File Error", "Could not open file.");
        return;
    }

    QString yamlFileName = fileName.split(".").first() + ".yaml";
    QFile yamlFile(yamlFileName);
    if (yamlFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream in(&inputFile);
        QTextStream out(&yamlFile);

        // Convert file content to YAML format
        while (!in.atEnd()) {
            QString line = in.readLine();
            out << "- " << line << "\n";
        }

        inputFile.close();
        yamlFile.close();

        QMessageBox::information(this, "YAML Created", "YAML file created successfully.");
    }
}

void MainWindow::trackDataChanges()
{
    if (savedData.isEmpty()) {
        savedData = {
            extractDeviceData(ui->deviceData1),
            extractDeviceData(ui->deviceData2),
            extractDeviceData(ui->deviceData3),
            extractDeviceData(ui->deviceData4),
            extractDeviceData(ui->deviceData5)
        };
    } else {
        QStringList currentData = {
            extractDeviceData(ui->deviceData1),
            extractDeviceData(ui->deviceData2),
            extractDeviceData(ui->deviceData3),
            extractDeviceData(ui->deviceData4),
            extractDeviceData(ui->deviceData5)
        };

        for (int i = 0; i < currentData.size(); ++i) {
            QString diff = calculateDifference(savedData[i], currentData[i]);
            QListWidget *deviceList = getDeviceListWidget(i);
            if (deviceList && deviceList->count() > 0) {
                QListWidgetItem *lastItem = deviceList->item(deviceList->count() - 1);
                QString updatedText = lastItem->text() + " [" + diff + "]";
                lastItem->setText(updatedText);
            }
        }

        savedData = currentData;
    }
}

QString MainWindow::extractDeviceData(QListWidget *deviceData)
{
    QStringList dataList;
    for (int i = 0; i < deviceData->count(); ++i) {
        dataList << deviceData->item(i)->text().split(":").last().trimmed();
    }
    return dataList.join(",");
}

QString MainWindow::calculateDifference(const QString &saved, const QString &current)
{
    QStringList savedList = saved.split(",");
    QStringList currentList = current.split(",");

    QStringList diffList;
    for (int i = 0; i < savedList.size(); ++i) {
        bool ok;
        int savedValue = savedList[i].toInt(&ok);
        int currentValue = currentList[i].toInt(&ok);

        int diff = currentValue - savedValue;
        diffList << "기준:[" + QString::number(savedValue) + "], 차이:" + QString::number(diff);
    }
    return diffList.join("; ");
}

QListWidget* MainWindow::getDeviceListWidget(int index)
{
    switch (index) {
        case 0: return ui->deviceData1;
        case 1: return ui->deviceData2;
        case 2: return ui->deviceData3;
        case 3: return ui->deviceData4;
        case 4: return ui->deviceData5;
        default: return nullptr;
    }
}
