#ifndef COG_ESTIMATION_H
#define COG_ESTIMATION_H

#define SENSOR_COUNT 4
#define LOCATION_COUNT 9
#define WINDOW_SIZE 30
#define INIT_SAMPLE_COUNT 49
extern const double loadingBoxWidth;
extern const double loadingBoxLength;
extern const double sensorCoords[SENSOR_COUNT][2];
extern const int locations[LOCATION_COUNT];
extern const double sensorWeights[SENSOR_COUNT];
extern const double initCenter[3];
extern const double xCenters[LOCATION_COUNT];
extern const double yCenters[LOCATION_COUNT];
extern const double zCenters[LOCATION_COUNT];
extern const double coefficient[LOCATION_COUNT];

int calculate_initial_values(const double samples[][SENSOR_COUNT], int sample_count, int init_values[SENSOR_COUNT]);
void apply_moving_average_filter(double value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, const double current_values[SENSOR_COUNT], double filtered_values[SENSOR_COUNT]);
void compute_deltas(const double current_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], double deltas[SENSOR_COUNT]);
int preprocess_data(const double sensor_values[SENSOR_COUNT], const int init_values[SENSOR_COUNT], double value_buffer[SENSOR_COUNT][WINDOW_SIZE], int buffer_counts[SENSOR_COUNT], int buffer_index, double deltas[SENSOR_COUNT]);
void calculate_cog(const double deltas[SENSOR_COUNT], double* xCenter, double* yCenter, double* zCenter);
void estimate_location(double xCenter, double yCenter, int* loc1, int* loc2, double* ratio1, double* ratio2);
double cal_distance_location(int location, double xCenter, double yCenter);
int estimate_weight(double zCenter, int i1, int i2, double ratio1, double ratio2);
void estimate_location_weight(double xCenter, double yCenter, double zCenter, int* combined_loc, int* weight);

#endif // COG_ESTIMATION_H
