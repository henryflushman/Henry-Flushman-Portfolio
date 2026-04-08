#include <Wire.h>
#include "myServo.h"

int mpu = 0x68;
long xOff = 0;
long yOff = 0;
long zOff = 0;

myServo::myServo(int servoPin, float mSecPerDegree, int zeroPulseWidth)
: _pin(servoPin),
  _usPerDeg(mSecPerDegree * 1000.0f),
  _zeroPulse(zeroPulseWidth)
{
  pinMode(_pin, OUTPUT);
  digitalWrite(_pin, LOW);
}

void myServo::_sendPulse(int microseconds) {
  digitalWrite(_pin, HIGH);
  delayMicroseconds(microseconds);
  digitalWrite(_pin, LOW);

  int rest = 20000 - microseconds;
  if (rest < 0) rest = 0;
  delayMicroseconds(rest);
}

void myServo::write(float degrees) {
  long pulse = (long)(_zeroPulse + degrees * _usPerDeg);
  if (pulse < 600)  pulse = 600;
  if (pulse > 2400) pulse = 2400;
  _sendPulse((int)pulse);
}

static void readAccelOnce(int16_t &ax, int16_t &ay, int16_t &az) {
  Wire.beginTransmission(mpu);
  Wire.write(0x3B);           // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(mpu, 6, true);
  ax = (Wire.read() << 8) | Wire.read();
  ay = (Wire.read() << 8) | Wire.read();
  az = (Wire.read() << 8) | Wire.read();
}

float readPitchDegrees() {
  int16_t ax, ay, az;
  readAccelOnce(ax, ay, az);

  long rx = ax - xOff;
  long ry = ay - yOff;
  long rz = az - zOff;

  float xg = rx / 16384.0;
  float yg = ry / 16384.0;
  float zg = rz / 16384.0;

  float pitch = atan2(-xg, sqrt(yg * yg + zg * zg)) * 57.3; // degrees
  return pitch;
}

void calibrateAccelerometer() {
  long xSum = 0;
  long ySum = 0;
  long zSum = 0;
  int samples = 100;

  Serial.println("Calibrating accelerometer... keep it still.");
  delay(500);


  for (int i = 0; i < samples; i++) {
    int16_t ax, ay, az;

    Wire.beginTransmission(mpu);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(mpu, 6, true);

    ax = Wire.read() << 8 | Wire.read();
    ay = Wire.read() << 8 | Wire.read();
    az = Wire.read() << 8 | Wire.read();

    xSum = xSum + ax;
    ySum = ySum + ay;
    zSum = zSum + az;
    delay(10);
  }

  xOff = xSum / samples;
  yOff = ySum / samples;
  zOff = zSum / samples;

  Serial.println("Calibration complete!");
  Serial.print("X offset: "); Serial.println(xOff);
  Serial.print("Y offset: "); Serial.println(yOff);
  Serial.print("Z offset: "); Serial.println(zOff);
}