#ifndef DATACHECKTOOL_H
#define DATACHECKTOOL_H

#include <QMainWindow>
#include <QListWidget>
#include <QLineEdit>

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void applyLoadLabel();
    void startRealTimeData();

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
};

#endif // DATACHECKTOOL_H
