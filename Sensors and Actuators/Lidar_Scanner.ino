#include <Wire.h>
#include <Adafruit_VL53L1X.h>
#include <Servo.h>

/* ------------------------- HARDWARE SETUP ------------------------- */

Adafruit_VL53L1X lidar;
Servo scan_servo;

/*
    Servo pin and angle limits
    - THETA_* are the "logical" scan angles in degrees (what Python expects)
    - SERVO_* map those logical angles into actual servo commands
*/

const int SERVO_PIN       = 9;

// logical scan limits (deg)
const int THETA_MIN_DEG   = -45;
const int THETA_MAX_DEG   =  45;
const int THETA_STEP_DEG  =   5;    // => 19 angle points

// servo command range for the scan
const int SERVO_MIN_DEG   = 60;     // command when angle = -45 deg
const int SERVO_MAX_DEG   = 120;    // command when angle = +45 deg

// timing (ms)
const unsigned long SERVO_SETTLE_MS   = 250;   // after each move
const unsigned long SAMPLE_WINDOW_MS  = 400;   // time spent collecting data per angle

// measurement filtering (mm)
const int RANGE_MIN_MM    = 50;     // throw away readings closer than this
const int RANGE_MAX_MM    = 3000;   // and farther than this

// simple serial protocol with Python
const char* CMD_START     = "START";
const char* MSG_SWEEP_DONE = "SWEEP_DONE";

String serial_buffer;


/* ------------------------- HELPER FUNCTIONS ----------------------- */

// map logical scan angle -> servo command, clamp into [0, 180]
int logical_to_servo_deg(int theta_deg)
{
    int servo_deg = map(theta_deg,
                        THETA_MIN_DEG, THETA_MAX_DEG,
                        SERVO_MIN_DEG, SERVO_MAX_DEG);

    if (servo_deg < 0)   servo_deg = 0;
    if (servo_deg > 180) servo_deg = 180;

    return servo_deg;
}


/* ------------------------- ARDUINO SETUP ------------------------- */

void setup()
{
    Serial.begin(115200);
    scan_servo.attach(SERVO_PIN);

    Wire.begin();
    if (!lidar.begin()) {
        Serial.println("VL53L1X not found, check wiring.");
        while (true) {
            // stuck here if sensor is missing
        }
    }

    lidar.startRanging();
}


/* ------------------------- MEASUREMENT LOGIC --------------------- */

// take measurements at one logical angle and print the average
void measure_at_angle(int theta_deg)
{
    // move servo
    int servo_deg = logical_to_servo_deg(theta_deg);
    scan_servo.write(servo_deg);
    delay(SERVO_SETTLE_MS);

    // average over SAMPLE_WINDOW_MS
    unsigned long t0 = millis();
    float sum_d = 0.0f;
    int   count = 0;

    while (millis() - t0 < SAMPLE_WINDOW_MS) {
        if (lidar.dataReady()) {
            int16_t d_mm = lidar.distance();     // raw distance (mm)
            lidar.clearInterrupt();

            // quick validity check
            if (d_mm > RANGE_MIN_MM && d_mm < RANGE_MAX_MM) {
                sum_d += d_mm;
                count++;
            }
        }
    }

    float avg_d_mm = -1.0f;
    if (count > 0) {
        avg_d_mm = sum_d / (float)count;
    }

    // Python expects: "angle_deg, distance_mm"
    Serial.print(theta_deg);
    Serial.print(", ");
    Serial.println(avg_d_mm);
}


// sweep from THETA_MIN_DEG to THETA_MAX_DEG
void run_sweep_once()
{
    for (int theta = THETA_MIN_DEG; theta <= THETA_MAX_DEG; theta += THETA_STEP_DEG) {
        measure_at_angle(theta);
    }
}


/* ---------------------------- MAIN LOOP -------------------------- */

void loop()
{
    // build up line until newline
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            // end of command
            if (serial_buffer.equals(CMD_START)) {
                // Python asked for a sweep
                run_sweep_once();
                Serial.println(MSG_SWEEP_DONE);
            }

            serial_buffer = "";   // reset buffer
        } else {
            serial_buffer += c;
        }
    }
}
