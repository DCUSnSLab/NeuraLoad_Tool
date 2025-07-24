
import numpy as np
cimport numpy as np

cdef extern from "COGMassEstimation.h":
    int calculate_initial_values(const double samples[][4], int sample_count, int init_values[4])
    void apply_moving_average_filter(double value_buffer[4][30], int buffer_counts[4], int buffer_index, const double current_values[4], double filtered_values[4])
    void compute_deltas(const double current_values[4], const int init_values[4], double deltas[4])
    int preprocess_data(const double sensor_values[4], const int init_values[4], double value_buffer[4][30], int buffer_counts[4], int buffer_index, double deltas[4])
    void calculate_cog(const double deltas[4], double* xCenter, double* yCenter, double* zCenter)
    void estimate_location(double xCenter, double yCenter, int* loc1, int* loc2, double* ratio1, double* ratio2)
    double cal_distance_location(int location, double xCenter, double yCenter)
    int estimate_weight(double zCenter, int i1, int i2, double ratio1, double ratio2)
    void estimate_location_weight(double xCenter, double yCenter, double zCenter, int* combined_loc, int* weight)

def init_sensor_values(np.ndarray[np.float64_t, ndim=2] samples):
    """
    센서 초기값 계산
    
    Args:
        samples: shape (N, 4)의 2D numpy 배열로 된 샘플 데이터
    Returns:
        list: 4개 센서의 초기값
    """
    cdef int init_values[4]
    cdef int sample_count = samples.shape[0]
    calculate_initial_values(<double(*)[4]>samples.data, sample_count, init_values)
    return [init_values[i] for i in range(4)]

def process_sensor_data(list sensor_values, list init_values, list buffer_counts, int buffer_index, list value_buffer):
    cdef double c_sensor_values[4]
    cdef int c_init_values[4]
    cdef int c_buffer_counts[4]
    cdef double c_value_buffer[4][30]
    cdef double deltas[4]

    for i in range(4):
        c_sensor_values[i] = sensor_values[i]
        c_init_values[i] = init_values[i]
        c_buffer_counts[i] = buffer_counts[i]
        for j in range(30):
            c_value_buffer[i][j] = value_buffer[i][j]

    buffer_index = preprocess_data(
        c_sensor_values,
        c_init_values,
        c_value_buffer,
        c_buffer_counts,
        buffer_index,
        deltas
    )

    for i in range(4):
        buffer_counts[i] = c_buffer_counts[i]
        for j in range(30):
            value_buffer[i][j] = c_value_buffer[i][j]

    return ([deltas[i] for i in range(4)], buffer_index)

def estimate_cog_position_weight(list deltas):
    """
    COG 위치와 무게 추정
    
    Args:
        deltas: 델타값 리스트 (4개)
        
    Returns:
        tuple: (위치, 무게)
    """
    cdef double c_deltas[4]
    cdef double xCenter, yCenter, zCenter
    cdef int combined_loc, weight
    
    # Python 리스트를 C 배열로 변환
    for i in range(4):
        c_deltas[i] = deltas[i]
    
    # COG 계산
    calculate_cog(c_deltas, &xCenter, &yCenter, &zCenter)
    
    # 위치와 무게 추정
    estimate_location_weight(xCenter, yCenter, zCenter, &combined_loc, &weight)
    
    return (combined_loc, weight)