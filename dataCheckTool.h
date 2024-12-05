#ifndef DATACHECKTOOL_H
#define DATACHECKTOOL_H

#include <QMainWindow>
#include <QListWidget>
#include <QLineEdit>
#include <QTimer>

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void applyLoadLabel();
    void startRealTimeData();

private:
    QListWidget *deviceData1;
    QListWidget *deviceData2;
    QListWidget *deviceData3;
    QListWidget *deviceData4;
    QListWidget *deviceData5;
    QListWidget *generalDataList;
    QLineEdit *loadInput;
};

#endif // DATACHECKTOOL_H
