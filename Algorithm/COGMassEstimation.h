#ifndef COG_ESTIMATION_H
#define COG_ESTIMATION_H

#define SENSOR_COUNT 4
#define LOCATION_COUNT 9
#define WINDOW_SIZE 30
#define INIT_SAMPLE_COUNT 50
#define LOADING_THRESHOLD 3.0f
#define WEIGHT_SAMPLES 50
#define COUNTS_TO_STABLE 50

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    STATE_IDLE,
    STATE_INIT,
    STATE_READY,
    STATE_LOADING,
    STATE_UNLOADING,
    STATE_STABILIZING,
    STATE_WEIGHTING
} LoadingState;

extern const float loadingBoxWidth;
extern const float loadingBoxLength;
extern const float sensorCoords[SENSOR_COUNT][2];
extern const int locations[LOCATION_COUNT];
extern const float sensorWeights[SENSOR_COUNT];
extern const float initCenter[3];
extern const float xCenters[LOCATION_COUNT];
extern const float yCenters[LOCATION_COUNT];
extern const float zCenters[LOCATION_COUNT];
extern const float coefficient[LOCATION_COUNT];

extern int init_values[SENSOR_COUNT];
extern int reset_algo_flag;

static float peak_value;
static float average_delta;
static bool cpt_estimation;
static bool init_complete_flag;
//int init_values[SENSOR_COUNT];
static int sample_count;
static float init_sums[SENSOR_COUNT];
static int init_count;

int check_sensor_status(const int sensor_values[SENSOR_COUNT]);
LoadingState detect_loading_state(const int sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT]);
LoadingState get_current_state(void);
const char* get_loading_state_string(LoadingState state);
float get_peak_value(void);
float get_baseline_value(void);
void reset_algorithm(void);
int calculate_initial_values(const int sensor_values[SENSOR_COUNT], int init_values[SENSOR_COUNT]);
void apply_moving_average_filter(float value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, const int current_values[SENSOR_COUNT], float filtered_values[SENSOR_COUNT]);
void compute_deltas(const float current_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], float deltas[SENSOR_COUNT]);
int preprocess_data(const int sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], float value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, float deltas[SENSOR_COUNT]);
void calculate_cog(const float deltas[SENSOR_COUNT], float* xCenter, float* yCenter, float* zCenter);
void estimate_location(float xCenter, float yCenter, int* loc1, int* loc2, float* ratio1, float* ratio2);
float cal_distance_location(int location, float xCenter, float yCenter);
int estimate_weight(float zCenter, int i1, int i2, float ratio1, float ratio2);
void estimate_location_weight(float xCenter, float yCenter, float zCenter, int* combined_loc, int* weight);
float get_average_delta(void);
int run_algo(const int sensor_values[SENSOR_COUNT]);

#ifdef __cplusplus
}
#endif

#endif // COG_ESTIMATION_H