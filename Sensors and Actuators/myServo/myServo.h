#ifndef MYSERVO_H
#define MYSERVO_H

#include <Arduino.h>

class myServo {
public:
  myServo(int servoPin, float mSecPerDegree, int zeroPulseWidth);
  void write(float degrees);

private:
  int   _pin;
  float _usPerDeg;
  int   _zeroPulse;
  void  _sendPulse(int microseconds);
};

void calibrateAccelerometer();
void readAccelOnce(int16_t &ax, int16_t &ay, int16_t &az);
float readPitchDegrees();

#endif
