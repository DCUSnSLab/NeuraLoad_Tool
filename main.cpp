#include <QApplication>
#include "dataCheckTool.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    
    MainWindow window; // MainWindow는 dataCheckTool.h에서 선언된 클래스입니다.
    window.setWindowTitle("Data Check Tool");
    window.resize(800, 600);
    window.show();

    return app.exec();
}
