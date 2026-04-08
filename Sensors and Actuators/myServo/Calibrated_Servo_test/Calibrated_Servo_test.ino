#include "Wire.h"
#include "myServo.h"

myServo servo(2, 0.007f, 1100);

void setup() {
  Wire.begin();
  Serial.begin(9600);

  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission(true);

  calibrateAccelerometer();
}

void loop() {
  float pitch = readPitchDegrees();

  if (pitch > 45) pitch = 45;
  if (pitch < -45) pitch = -45;

  servo.write(pitch);

  Serial.print("pitch: ");
  Serial.println(pitch);

  delay(100);
}