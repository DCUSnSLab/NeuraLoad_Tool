#include "COGMassEstimation.h"
#include <string.h> // memset
#include <math.h>   // fabs
#include <stdio.h>

const double loadingBoxWidth = 1630.0;
const double loadingBoxLength = 2860.0;

const double sensorCoords[SENSOR_COUNT][2] = {
    {373.1, 1.0},
    {201.0, 2516.9},
    {1256.9, 1.0},
    {1429.0, 2516.9}
};

const int locations[LOCATION_COUNT] = {1,2,3,4,5,6,7,8,9};
const double sensorWeights[SENSOR_COUNT] = {1.0, 0.45, 1.0, 0.45};
const double initCenter[3] = {815.0, 1430.0, 0.0};

const double xCenters[LOCATION_COUNT] = {794.3329811, 813.9314133, 833.8338401, 791.8779953, 812.5496202, 830.3194796, 795.4399509, 814.2261959, 834.6214622};
const double yCenters[LOCATION_COUNT] = {1416.042594, 1416.207189, 1415.538152, 1431.776203, 1429.261099, 1430.5897, 1447.795189, 1446.468957, 1447.492051};
const double zCenters[LOCATION_COUNT] = {13.9859375, 15.51666667, 14.2640625, 16.65625, 16.3, 15.884375, 15.31041667, 15.61875, 15.29375};
const double coefficient[LOCATION_COUNT] = {34.305925, 31.019686, 33.7840643, 28.4172494, 28.3819276, 29.24740398, 29.14227469, 25.70094819, 29.02068168};

int calculate_initial_values(const double samples[][SENSOR_COUNT], int sample_count, int init_values[SENSOR_COUNT]) {
    if(sample_count <= 0) return 0;
    double sums[SENSOR_COUNT] = {0};
    for(int i=0; i<sample_count; i++) {
        for(int j=0; j<SENSOR_COUNT; j++) {
            sums[j] += samples[i][j];
        }
    }
    for(int j=0; j<SENSOR_COUNT; j++) {
        init_values[j] = (int)(sums[j] / sample_count);
    }
    return 1;
}

void apply_moving_average_filter(double value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, const double current_values[SENSOR_COUNT], double filtered_values[SENSOR_COUNT]) {
    for(int i=0; i<SENSOR_COUNT; i++) {
        value_buffer[i][buffer_index] = current_values[i];
        if(buffer_counts[i] < WINDOW_SIZE) buffer_counts[i]++;
        double sum = 0.0;
        for(int k=0; k<buffer_counts[i]; k++) {
            sum += value_buffer[i][k];
        }
        filtered_values[i] = sum / buffer_counts[i];
    }
}


void compute_deltas(const double current_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], double deltas[SENSOR_COUNT]) {
    for(int i=0; i<SENSOR_COUNT; i++) {
        deltas[i] = (double)init_values[i] - current_values[i];
    }
}

int preprocess_data(const double sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], double value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, double deltas[SENSOR_COUNT]) {
    double filtered[SENSOR_COUNT] = {0};
    apply_moving_average_filter(value_buffer, buffer_counts, buffer_index, sensor_values, filtered);

    for (int i = 0; i < SENSOR_COUNT; i++) {
        printf("%.9f ", filtered[i]);
    }
    printf("\n");

    compute_deltas(filtered, init_values, deltas);


    buffer_index = (buffer_index + 1) % WINDOW_SIZE;

    return buffer_index;
}

void calculate_cog(const double deltas[SENSOR_COUNT], double* xCenter, double* yCenter, double* zCenter) {
    double weightDeltas[SENSOR_COUNT];
    for (int i = 0; i < SENSOR_COUNT; i++) {
        weightDeltas[i] = deltas[i] * sensorWeights[i];
    }
    double roll = ((weightDeltas[0] - weightDeltas[2]) + (weightDeltas[1] - weightDeltas[3])) / (((sensorCoords[3][0] - sensorCoords[1][0]) + (sensorCoords[2][0] - sensorCoords[0][0])) / 2.0);
    double pitch = ((weightDeltas[0] - weightDeltas[1]) + (weightDeltas[2] - weightDeltas[3])) / (((sensorCoords[3][1] - sensorCoords[2][1]) + (sensorCoords[1][1] - sensorCoords[0][1])) / 2.0);
    *xCenter = (loadingBoxWidth / 2.0) - roll * (loadingBoxWidth / 2.0);
    *yCenter = (loadingBoxLength / 2.0) - pitch * (loadingBoxLength / 2.0);
    *zCenter = (deltas[0] + deltas[1] + deltas[2] + deltas[3]) / 4.0;
    // printf("[%lf, %lf, %lf, %lf]\n", deltas[0], deltas[1], deltas[2], deltas[3]);
}

void estimate_location(double xCenter, double yCenter, int* loc1, int* loc2, double* ratio1, double* ratio2) {
    double point[2] = {xCenter, yCenter};
    int non_center_indices[LOCATION_COUNT - 1];
    int count = 0;

    for (int i = 0; i < LOCATION_COUNT; i++) {
        if (locations[i] != 5) non_center_indices[count++] = i;
    }

    double min_dist = 1e30;
    int min_idx = -1;
    for (int i = 0; i < count; i++) {
        int idx = non_center_indices[i];
        double dx = point[0] - xCenters[idx];
        double dy = point[1] - yCenters[idx];
        double dist = sqrt(dx * dx + dy * dy);
        if (dist < min_dist) {
            min_dist = dist;
            min_idx = idx;
        }
    }

    int closest_loc = locations[min_idx];

    int neighbors_map[][2] = {
        {2, 4}, // 1
        {1, 3}, // 2
        {2, 6}, // 3
        {1, 7}, // 4
        {0, 0}, // 5 없음
        {3, 9}, // 6
        {4, 8}, // 7
        {7, 9}, // 8
        {6, 8}  // 9
    };

    int* adj = neighbors_map[closest_loc - 1];

    double dist2 = 1e30;
    int loc2_idx = -1;
    int loc2_val = 0;

    for (int i = 0; i < 2; i++) {
        if (adj[i] == 0) continue;
        int adj_loc = adj[i];
        int adj_idx = -1;
        for (int j = 0; j < LOCATION_COUNT; j++) {
            if (locations[j] == adj_loc) {
                adj_idx = j;
                break;
            }
        }
        if (adj_idx == -1) continue;
        double dx = point[0] - xCenters[adj_idx];
        double dy = point[1] - yCenters[adj_idx];
        double dist = sqrt(dx * dx + dy * dy);
        if (dist < dist2) {
            dist2 = dist;
            loc2_idx = adj_idx;
            loc2_val = adj_loc;
        }
    }

    *loc1 = closest_loc;
    *loc2 = loc2_val;

    if (min_dist + dist2 == 0.0) {
        *ratio1 = 0.5;
        *ratio2 = 0.5;
    } else {
        *ratio1 = dist2 / (min_dist + dist2);
        *ratio2 = min_dist / (min_dist + dist2);
    }
}

double cal_distance_location(int location, double xCenter, double yCenter) {
    int idx = -1;
    for(int i=0; i<LOCATION_COUNT; i++) {
        if(locations[i] == location) {
            idx = i;
            break;
        }
    }
    if(idx == -1) return -1.0;

    double a = (yCenters[idx] - initCenter[1]) / (xCenters[idx] - initCenter[0]);
    double b = -1.0;
    double c = a * initCenter[0] - initCenter[1];

    return fabs(a * xCenter + b * yCenter + c) / sqrt(a*a + b*b);
}


int estimate_weight(double zCenter, int i1, int i2, double ratio1, double ratio2) {
    if(zCenter <= 0.0) return 0;
    double loc1_weight = coefficient[i1] * zCenter;
    double loc2_weight = coefficient[i2] * zCenter;

    double threshold1 = zCenters[i1] / 5.0;
    double threshold15 = threshold1 * 1.5;
    double threshold2 = zCenters[i2] / 5.0;
    double threshold25 = threshold2 * 1.5;

    double coeff1, coeff2;

    if(zCenter <= threshold1) coeff1 = 1.4;
    else if(zCenter <= threshold15) coeff1 = 1.2;
    else coeff1 = 1.0;

    if(zCenter <= threshold2) coeff2 = 1.4;
    else if(zCenter <= threshold25) coeff2 = 1.2;
    else coeff2 = 1.0;

    double weight1 = coeff1 * loc1_weight * ratio2;
    double weight2 = coeff2 * loc2_weight * ratio1;
    printf("weight1: %lf, weight2: %lf, coeff1: %lf, coeff2: %lf, i1: %d, i2: %d, coefficient[i1]: %lf, coefficient[i2]: %lf, zCenter: %lf\n", weight1, weight2, coeff1, coeff2, i1, i2, coefficient[i1], coefficient[i2], zCenter);
    return (int)(weight1 + weight2);
}

// 위치 및 무게 최종 추정 함수
void estimate_location_weight(double xCenter, double yCenter, double zCenter, int* combined_loc, int* weight) {
    int loc1, loc2;
    double ratio1, ratio2;
    estimate_location(xCenter, yCenter, &loc1, &loc2, &ratio1, &ratio2);

    double dist1 = cal_distance_location(loc1, xCenter, yCenter);
    double dist2 = cal_distance_location(loc2, xCenter, yCenter);

    double total_dist = dist1 + dist2;
    if(total_dist == 0.0) {
        ratio1 = 0.5;
        ratio2 = 0.5;
    } else {
        ratio1 = dist2 / total_dist;
        ratio2 = dist1 / total_dist;
    }

    *weight = estimate_weight(zCenter, loc1 - 1, loc2 - 1, ratio1, ratio2);
    *combined_loc = loc1 * 10 + loc2;
}
