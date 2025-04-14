## 화물과적 중심  탄소중립을 위한 주행 데이터 수집 장치 및 관리 시스템

### 키보드 이벤트 정리
P: 무게+

O: 무게-

I: 무게 리셋

M: save

K: 멈춤

L: 재시작

무게 테이블 선택

Q W E

A S D

Z X C

### 알고리즘 구현 관련 내용 작성

 - 사용할 모델 파일은 model 경로에 입력
   - 이후 AlgorithmBase를 상속받아 작성한 각자의 클래스 생성자의 model_path에 해당 경로를 입력한다

 - Popen을 통한 알고리즘 프로세스 생성 및 결과 반영
   - 현재 구조에서는 아래 흐름을 통해 알고리즘 수행 결과를 확인
     - experiment.py 의 run_algorithms_as_subprocess() 함수 호출
       - run_algorithms_as_subprocess() 함수는 run_algorithm.py를 별도의 프로세스로 호출하면서 실행 인자 전달
         - algorithm.py의 129번 라인
       - run_algorithm.py는 입력받은 내용에 따라 호출할 알고리즘을 선택하고 해당 알고리즘의 입력 전달
       - *중요* 각 알고리즘의 실행 결과는 run_algorithm.py의 85번 라인 result 출력을 통해 전달함
         - 이 부분은 프로세스간 통신(IPC)을 사용하여 추후 개선 필요함