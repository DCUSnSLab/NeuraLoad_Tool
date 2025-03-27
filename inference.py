import json
import numpy as np
import joblib

# 저장된 모델 불러오기
model = joblib.load("20250327_RF_Model.joblib")

# 내 모델 말고도 혁규, 준현이 구현한 알고리즘을 사용해서도 동작해야 하기 때문에 입력값과 출력값은 아래처럼 고정해야 함

# 알고리즘의 입출력 인터페이스
# 입력 float(Laser1), float(Laser2), float(Laser3), float(Laser4)
# 출력 int(Position), float(Weight)

# sample 안에 있는 값 4개는 각각 레이저 센서의 값을 의미
sample = [
    [613,
    649,
    606,
    673]
]

sample = np.array(sample)

# 모델 예측
predictions = model.predict(sample)
predicted_weights = predictions[:, 0]
predicted_positions = predictions[:, 1]
# Position 예측은 정수형이므로 반올림 처리
predicted_positions_rounded = np.rint(predicted_positions).astype(int)

# 출력값의 경우

print(predicted_weights)
print(predicted_positions_rounded)