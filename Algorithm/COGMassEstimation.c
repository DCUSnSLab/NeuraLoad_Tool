#include "COGMassEstimation.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

int reset_algo_flag = 0;
const float loadingBoxWidth = 1630.0f;
const float loadingBoxLength = 2860.0f;

const float sensorCoords[SENSOR_COUNT][2] = {
    {373.1f, 1.0f},
    {201.0f, 2516.9f},
    {1256.9f, 1.0f},
    {1429.0f, 2516.9f}
};

const int locations[LOCATION_COUNT] = {1,2,3,4,5,6,7,8,9};
const float sensorWeights[SENSOR_COUNT] = {1.0f, 0.45f, 1.0f, 0.45f};
const float initCenter[3] = {815.0f, 1430.0f, 0.0f};
const float xCenters[LOCATION_COUNT] = {794.3329811f, 813.9314133f, 833.8338401f, 791.8779953f, 812.5496202f, 830.3194796f, 795.4399509f, 814.2261959f, 834.6214622f};
const float yCenters[LOCATION_COUNT] = {1416.042594f, 1416.207189f, 1415.538152f, 1431.776203f, 1429.261099f, 1430.5897f, 1447.795189f, 1446.468957f, 1447.492051f};
const float zCenters[LOCATION_COUNT] = {13.9859375f, 15.51666667f, 14.2640625f, 16.65625f, 16.3f, 15.884375f, 15.31041667f, 15.61875f, 15.29375f};
const float coefficient[LOCATION_COUNT] = {34.305925f, 31.019686f, 33.7840643f, 28.4172494f, 28.3819276f, 29.24740398f, 29.14227469f, 25.70094819f, 29.02068168f};

static LoadingState current_state = STATE_IDLE;
static float peak_value = 0.0f;
static float average_delta = 0.0f;
static float baseline_value = 0.0f;
static float valley_value = 0.0f;
static bool cpt_estimation = false;
static bool init_complete_flag = false;
int init_values[SENSOR_COUNT] = {0};
static int sample_count = 0;
static float init_sums[SENSOR_COUNT] = {0};
static int init_count = 0;

const char* get_loading_state_string(LoadingState state) {
    switch(state) {
        case STATE_IDLE: return "IDLE";
        case STATE_INIT: return "INIT";
        case STATE_READY: return "READY";
        case STATE_LOADING: return "LOADING";
        case STATE_UNLOADING: return "UNLOADING";
        case STATE_STABILIZING: return "STABILIZING";
        case STATE_WEIGHTING: return "WEIGHTING";
        default: return "UNKNOWN";
    }
}

int check_sensor_status(const int sensor_values[SENSOR_COUNT]) {
    for (int i = 0; i < SENSOR_COUNT; i++) {
        if (sensor_values[i] <= 0 || sensor_values[i] > 1000) {
            return 0;
        }
    }
    return 1;
}

int calculate_initial_values(const int sensor_values[SENSOR_COUNT], int init_values[SENSOR_COUNT]) {
    extern int reset_algo_flag;
    if (reset_algo_flag) {
        memset(init_sums, 0, sizeof(init_sums));
        init_count = 0;
        reset_algo_flag = 0;
    }

    if (init_count >= INIT_SAMPLE_COUNT) return 1;

    for (int i = 0; i < SENSOR_COUNT; i++) {
        init_sums[i] += sensor_values[i];
    }
    init_count++;

    if (init_count == INIT_SAMPLE_COUNT) {
        for (int i = 0; i < SENSOR_COUNT; i++) {
            init_values[i] = (int)(init_sums[i] / INIT_SAMPLE_COUNT);
        }
        return 1;
    }

    return 0;
}

float get_peak_value(void) {
    return peak_value;
}

float get_baseline_value(void) {
    return baseline_value;
}

float get_average_delta(void) {
    return average_delta;
}

LoadingState detect_loading_state(const int sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT]) {
    static int stability_counter = 0;
    static LoadingState last_state = STATE_IDLE;

    if (reset_algo_flag) {
        current_state = STATE_IDLE;
        peak_value = 0.0f;
        average_delta = 0.0f;
        stability_counter = 0;
        cpt_estimation = 0;
        last_state = STATE_IDLE;
    }

    float current_total_delta = 0.0f;
    for (int i = 0; i < SENSOR_COUNT; i++) {
        if (init_values[i] != 0) {
            current_total_delta += (float)init_values[i] - (float)sensor_values[i];
        }
    }

    if (SENSOR_COUNT > 0) {
        average_delta = current_total_delta;
    }

    switch (current_state) {
        case STATE_IDLE:
            peak_value = 0;
            current_state = STATE_INIT;
            break;

        case STATE_INIT:
            if (init_complete_flag) {
                current_state = STATE_READY;
                init_complete_flag = 0;
            }
            break;

        case STATE_READY:
            if (current_total_delta >= baseline_value + LOADING_THRESHOLD) {
                current_state = STATE_LOADING;
                peak_value = current_total_delta;
                last_state = STATE_LOADING;
                stability_counter = 0;
            } else if (current_total_delta <= baseline_value - LOADING_THRESHOLD) {
                current_state = STATE_UNLOADING;
                valley_value = current_total_delta;
                last_state = STATE_UNLOADING;
                stability_counter = 0;
            }
            break;

        case STATE_LOADING:
            last_state = STATE_LOADING;
            if (current_total_delta >= peak_value) {
                peak_value = current_total_delta;
                stability_counter = 0;
            } else {
                current_state = STATE_STABILIZING;
                stability_counter = 0;
            }
            break;

        case STATE_UNLOADING:
            last_state = STATE_UNLOADING;
            if (current_total_delta <= valley_value) {
                valley_value = current_total_delta;
                stability_counter = 0;
            } else {
                current_state = STATE_STABILIZING;
                stability_counter = 0;
            }
            break;

        case STATE_STABILIZING:
            if (last_state == STATE_LOADING) {
                if (current_total_delta >= peak_value) {
                    current_state = STATE_LOADING;
                    peak_value = current_total_delta;
                    stability_counter = 0;
                }
                else {
                    stability_counter++;
                }
            }
            else if (last_state == STATE_UNLOADING) {
                if (current_total_delta <= valley_value) {
                    current_state = STATE_UNLOADING;
                    valley_value = current_total_delta;
                    stability_counter = 0;
                }
                else {
                    stability_counter++;
                }
            }

            if (stability_counter >= COUNTS_TO_STABLE) {
                current_state = STATE_WEIGHTING;
                stability_counter = 0;
            }
            break;

        case STATE_WEIGHTING:
            if(cpt_estimation) {
                current_state = STATE_READY;
                cpt_estimation = false;
                baseline_value = current_total_delta;
                peak_value = baseline_value;
                valley_value = baseline_value;
                stability_counter = 0;
            }
            else {
                if (current_total_delta >= peak_value + LOADING_THRESHOLD) {
                    current_state = STATE_LOADING;
                    peak_value = current_total_delta;
                    last_state = STATE_LOADING;
                    stability_counter = 0;
                    sample_count = 0;
                }
                else if (current_total_delta <= valley_value - LOADING_THRESHOLD) {
                    current_state = STATE_UNLOADING;
                    valley_value = current_total_delta;
                    last_state = STATE_UNLOADING;
                    stability_counter = 0;
                    sample_count = 0;
                }
            }
            break;
    }
    return current_state;
}

LoadingState get_current_state() {
    return current_state;
}

void compute_deltas(const float current_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], float deltas[SENSOR_COUNT]) {
    for(int i=0; i<SENSOR_COUNT; i++) {
        deltas[i] = (float)init_values[i] - current_values[i];
    }
}

void apply_moving_average_filter(float value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, const int current_values[SENSOR_COUNT], float filtered_values[SENSOR_COUNT]) {
    for (int i = 0; i < SENSOR_COUNT; i++) {
        value_buffer[i][buffer_index] = current_values[i];
        if (buffer_counts[i] < WINDOW_SIZE) buffer_counts[i]++;
        float sum = 0.0f;
        for (int k = 0; k < buffer_counts[i]; k++) {
            sum += value_buffer[i][k];
        }
        filtered_values[i] = sum / buffer_counts[i];
    }
}

int preprocess_data(const int sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], float value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, float deltas[SENSOR_COUNT]) {
    float filtered[SENSOR_COUNT] = {0};
    apply_moving_average_filter(value_buffer, buffer_counts, buffer_index, sensor_values, filtered);
    compute_deltas(filtered, init_values, deltas);
    buffer_index = (buffer_index + 1) % WINDOW_SIZE;
    return buffer_index;
}

void calculate_cog(const float deltas[SENSOR_COUNT], float* xCenter, float* yCenter, float* zCenter) {
    float weightDeltas[SENSOR_COUNT];
    for (int i = 0; i < SENSOR_COUNT; i++) {
        weightDeltas[i] = deltas[i] * sensorWeights[i];
    }
    float roll = ((weightDeltas[0] - weightDeltas[2]) + (weightDeltas[1] - weightDeltas[3])) / (((sensorCoords[3][0] - sensorCoords[1][0]) + (sensorCoords[2][0] - sensorCoords[0][0])) / 2.0f);
    float pitch = ((weightDeltas[0] - weightDeltas[1]) + (weightDeltas[2] - weightDeltas[3])) / (((sensorCoords[3][1] - sensorCoords[2][1]) + (sensorCoords[1][1] - sensorCoords[0][1])) / 2.0f);
    *xCenter = (loadingBoxWidth / 2.0f) - roll * (loadingBoxWidth / 2.0f);
    *yCenter = (loadingBoxLength / 2.0f) - pitch * (loadingBoxLength / 2.0f);
    *zCenter = (weightDeltas[0] + weightDeltas[1] + weightDeltas[2] + weightDeltas[3]) / 4.0f;
}

void estimate_location(float xCenter, float yCenter, int* loc1, int* loc2, float* ratio1, float* ratio2) {
    float point[2] = {xCenter, yCenter};
    int non_center_indices[LOCATION_COUNT - 1];
    int count = 0;

    for (int i = 0; i < LOCATION_COUNT; i++) {
        if (locations[i] != 5) non_center_indices[count++] = i;
    }

    float min_dist = 1e30f;
    int min_idx = -1;
    for (int i = 0; i < count; i++) {
        int idx = non_center_indices[i];
        float dx = point[0] - xCenters[idx];
        float dy = point[1] - yCenters[idx];
        float dist = sqrtf(dx * dx + dy * dy);
        if (dist < min_dist) {
            min_dist = dist;
            min_idx = idx;
        }
    }

    int closest_loc = locations[min_idx];

    int neighbors_map[][2] = {
        {2, 4}, {1, 3}, {2, 6}, {1, 7}, {0, 0},
        {3, 9}, {4, 8}, {7, 9}, {6, 8}
    };

    int* adj = neighbors_map[closest_loc - 1];
    float dist2 = 1e30f;
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
        float dx = point[0] - xCenters[adj_idx];
        float dy = point[1] - yCenters[adj_idx];
        float dist = sqrtf(dx * dx + dy * dy);
        if (dist < dist2) {
            dist2 = dist;
            loc2_idx = adj_idx;
            loc2_val = adj_loc;
        }
    }

    *loc1 = closest_loc;
    *loc2 = loc2_val;

    if (min_dist + dist2 == 0.0f) {
        *ratio1 = 0.5f;
        *ratio2 = 0.5f;
    } else {
        *ratio1 = dist2 / (min_dist + dist2);
        *ratio2 = min_dist / (min_dist + dist2);
    }
}

float cal_distance_location(int location, float xCenter, float yCenter) {
    int idx = -1;
    for(int i=0; i<LOCATION_COUNT; i++) {
        if(locations[i] == location) {
            idx = i;
            break;
        }
    }
    if(idx == -1) return -1.0f;

    float a = (yCenters[idx] - initCenter[1]) / (xCenters[idx] - initCenter[0]);
    float b = -1.0f;
    float c = a * initCenter[0] - initCenter[1];

    float distance = fabsf(a * xCenter + b * yCenter + c) / sqrtf(a*a + b*b);
    distance = roundf(distance * 1e6f) / 1e6f;

    return distance;
}

int estimate_weight(float zCenter, int i1, int i2, float ratio1, float ratio2) {
    if(zCenter <= 0.0f) return 0;
    float loc1_weight = coefficient[i1] * zCenter;
    float loc2_weight = coefficient[i2] * zCenter;

    float threshold1 = zCenters[i1] / 5.0f;
    float threshold15 = threshold1 * 1.5f;
    float threshold2 = zCenters[i2] / 5.0f;
    float threshold25 = threshold2 * 1.5f;

    float coeff1, coeff2;

    if(zCenter <= threshold1) coeff1 = 1.4f;
    else if(zCenter <= threshold15) coeff1 = 1.2f;
    else coeff1 = 1.0f;

    if(zCenter <= threshold2) coeff2 = 1.4f;
    else if(zCenter <= threshold25) coeff2 = 1.2f;
    else coeff2 = 1.0f;

    float weight1 = coeff1 * loc1_weight * ratio2;
    float weight2 = coeff2 * loc2_weight * ratio1;
    return (int)(weight1 + weight2);
}

void estimate_location_weight(float xCenter, float yCenter, float zCenter, int* combined_loc, int* weight) {
    int loc1, loc2;
    float ratio1, ratio2;
    estimate_location(xCenter, yCenter, &loc1, &loc2, &ratio1, &ratio2);

    float dist1 = cal_distance_location(loc1, xCenter, yCenter);
    float dist2 = cal_distance_location(loc2, xCenter, yCenter);

    float total_dist = dist1 + dist2;
    if(total_dist == 0.0f) {
        ratio1 = 0.5f;
        ratio2 = 0.5f;
    } else {
        ratio1 = dist2 / total_dist;
        ratio2 = dist1 / total_dist;
    }

    *weight = estimate_weight(zCenter, loc1 - 1, loc2 - 1, ratio1, ratio2);
    *combined_loc = loc1 * 10 + loc2;
}

void reset_algorithm() {
    reset_algo_flag = 1;
    memset(init_sums, 0, sizeof(init_sums));
    init_count = 0;
}

int run_algo(const int sensor_values[SENSOR_COUNT]) {
    static float value_buffer[SENSOR_COUNT][WINDOW_SIZE] = {0};
    static int buffer_counts[SENSOR_COUNT] = {0};
    static int buffer_index = 0;
    static int initialized = 0;
    static LoadingState current_loading_state = STATE_IDLE;

    static int weight_samples[WEIGHT_SAMPLES] = {0};

    static int final_average_weight = 0;
    static bool is_collection_complete = false;

    if (reset_algo_flag) {
        initialized = 0;
        sample_count = 0;
        final_average_weight = 0;
        is_collection_complete = false;
        memset(weight_samples, 0, sizeof(weight_samples));
        init_count = 0;
        current_loading_state = STATE_IDLE;
        reset_algo_flag = 1;
    }

    if (!check_sensor_status(sensor_values)) {
        return -1;
    }

    current_loading_state = detect_loading_state(sensor_values, init_values);

    switch (current_loading_state) {
        case STATE_READY:
            sample_count = 0;
            memset(weight_samples, 0, sizeof(weight_samples));
            break;
        case STATE_INIT:
            if (!initialized) {
                if (calculate_initial_values(sensor_values, init_values)) {
                    initialized = 1;
                    init_complete_flag = true;
                }
            }
            break;

        case STATE_WEIGHTING:
            if (is_collection_complete) {
                cpt_estimation = true;
                is_collection_complete = false;
                return final_average_weight;
            }

            float deltas[SENSOR_COUNT];
            buffer_index = preprocess_data(sensor_values, init_values, value_buffer, buffer_counts, buffer_index, deltas);

            float xCenter, yCenter, zCenter;
            calculate_cog(deltas, &xCenter, &yCenter, &zCenter);

            int combined_loc = 0;
            int current_weight = 0;
            estimate_location_weight(xCenter, yCenter, zCenter, &combined_loc, &current_weight);

            if (sample_count < WEIGHT_SAMPLES) {
                weight_samples[sample_count++] = current_weight;
            }

            if (sample_count >= WEIGHT_SAMPLES) {
                float sum = 0.0f;

                for (int i = 0; i < sample_count; i++) {
                    sum += weight_samples[i];
                }
                final_average_weight = (int)(sum / sample_count);

                is_collection_complete = true;
                return final_average_weight;
            }
            break;
    }
    return 0+final_average_weight;
}