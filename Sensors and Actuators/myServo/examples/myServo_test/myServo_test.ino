#include "myServo.h"

myServo servo(2, 0.007f, 1100);

void setup() {
  Serial.begin(9600);
  calibrateAccelerometer(A0,A1,A2);
  Serial.println("myServo Test: Outputting Pulse Widths...");
}

void loop() {
  float angleList[] = {0, 45, 90, 135, 180};
  int numAngles = 5;

  for (int i = 0; i < numAngles; i++) {
    float angle = angleList[i];

    float pulseWidth = 1500 + angle * (0.0055 * 1000.0); // convert ms/deg → µs/deg
    if (pulseWidth < 600) pulseWidth = 600;
    if (pulseWidth > 2400) pulseWidth = 2400;

    servo.write(angle);
    Serial.print("Angle: ");
    Serial.print(angle);
    Serial.print(" deg, Pulse Width: ");
    Serial.print(pulseWidth);
    Serial.println(" µs");

    unsigned long start = millis();
    while (millis() - start < 600) {
      servo.write(angle);  // maintain the signal
    }
  }
}
