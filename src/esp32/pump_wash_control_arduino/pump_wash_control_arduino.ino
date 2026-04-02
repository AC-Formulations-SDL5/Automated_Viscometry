// Commented cause of IDE compatability, USE Arduino IDE for running, testing and uploading the code.

#include <Arduino.h>
// Driver 1 (Pump 1, Pump 2)
#define ENABLE1 25
#define IN1     27
#define IN2     14
#define ENABLE2 33
#define IN3     32 
#define IN4     23

// Driver 2 (Pump 3, Pump 4)
#define ENABLE3 26
#define IN5     13
#define IN6     12
#define ENABLE4 18
#define IN7     19
#define IN8     21

// Driver 3 (Pump 5, Pump 6)
#define ENABLE5 22
#define IN9     5
#define IN10    17
#define ENABLE6 16
#define IN11    4
#define IN12    2

// PWM setup
const int pwmFreq = 1000;    // PWM frequency
const int pwmResolution = 8; // 8-bit resolution (0-255)

// Motor speeds (converted from Arduino Mega values)
const int speedPWM_A = 170; // Pump 1 speed
const int speedPWM_B = 170; // Pump 2 speed
const int speedPWM_C = 170; // Pump 3 speed
const int speedPWM_D = 170; // Pump 4 speed
const int speedPWM_E = 210; // Pump 5 speed
const int speedPWM_F = 210; // Pump 6 speed
const int speedPWM_G = 160; // Washer 1 speed (using Driver 1)
const int speedPWM_H = 160; // Washer 2 speed (using Driver 2)
const int speedPWM_I = 160; // Washer 3 speed (using Driver 3)

#define PUMP_STAGE_TIME  10000  // Initial pump stage: 10 seconds 
#define WASH_STAGE_TIME  60000  // 12V DC motor wash cycle: 60 seconds
#define RINSE_STAGE_TIME 15000  // Reverse rinse cycle: 15 seconds

void setup() {
  // Setup motor control pins
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(IN5, OUTPUT); pinMode(IN6, OUTPUT);
  pinMode(IN7, OUTPUT); pinMode(IN8, OUTPUT);
  pinMode(IN9, OUTPUT); pinMode(IN10, OUTPUT);
  pinMode(IN11, OUTPUT); pinMode(IN12, OUTPUT);
  
  // Setup PWM channels using new API
  ledcAttach(ENABLE1, pwmFreq, pwmResolution);
  ledcAttach(ENABLE2, pwmFreq, pwmResolution);
  ledcAttach(ENABLE3, pwmFreq, pwmResolution);
  ledcAttach(ENABLE4, pwmFreq, pwmResolution);
  ledcAttach(ENABLE5, pwmFreq, pwmResolution);
  ledcAttach(ENABLE6, pwmFreq, pwmResolution);
  
  Serial.begin(115200);
  Serial.println("Send '1', '2', or '3' to run specific wash station, '0' to stop all.");
}

// Main loop 
void loop() {
  if (Serial.available()) {
    char input = Serial.read();
    if (input == '1') {
      Serial.println("Starting Wash Station 1...");
      washStation1();
    } else if (input == '2') {
      Serial.println("Starting Wash Station 2...");
      washStation2();
    } else if (input == '3') {
      Serial.println("Starting Wash Station 3...");
      washStation3();
    } else if (input == '0') {
      Serial.println("Emergency STOP received!");
      stopAll();
    }
  }
}

// Pumps 1, 2 + Washer 1 motor (using Driver 1)
void washStation1() {
  // Stage 1: Run Pump 1 only for 10 seconds
  Serial.println("Stage 1: Starting Pump 1 for 10 seconds");
  runMotor(IN1, IN2, ENABLE1, speedPWM_A);
  delay(PUMP_STAGE_TIME);
  stopMotor(IN1, IN2, ENABLE1);
  
  // Stage 2: Run Washer 1 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC motor for 60 seconds");
  runMotor(IN3, IN4, ENABLE2, speedPWM_G);
  delay(WASH_STAGE_TIME);
  stopMotor(IN3, IN4, ENABLE2);
  
  // Stage 3: Run Pump 2 (reverse) for 15 seconds
  Serial.println("Stage 3: Starting Pump 2 (reverse) for 15 seconds");
  runMotorReverse(IN1, IN2, ENABLE1, speedPWM_B);
  delay(RINSE_STAGE_TIME);
  stopMotor(IN1, IN2, ENABLE1);
  
  Serial.println("Wash Station 1 DONE - New Sequence Complete");
}

// Pumps 3, 4 + Washer 2 motor (using Driver 2)
void washStation2() {
  // Stage 1: Run Pump 3 only for 10 seconds
  Serial.println("Stage 1: Starting Pump 3 for 10 seconds");
  runMotor(IN5, IN6, ENABLE3, speedPWM_C);
  delay(PUMP_STAGE_TIME);
  stopMotor(IN5, IN6, ENABLE3);
  
  // Stage 2: Run Washer 2 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC motor for 60 seconds");
  runMotor(IN7, IN8, ENABLE4, speedPWM_H);
  delay(WASH_STAGE_TIME);
  stopMotor(IN7, IN8, ENABLE4);
  
  // Stage 3: Run Pump 4 (reverse) for 15 seconds
  Serial.println("Stage 3: Starting Pump 4 (reverse) for 15 seconds");
  runMotorReverse(IN5, IN6, ENABLE3, speedPWM_D);
  delay(RINSE_STAGE_TIME);
  stopMotor(IN5, IN6, ENABLE3);
  
  Serial.println("Wash Station 2 DONE - New Sequence Complete");
}

// Pumps 5, 6 + Washer 3 motor (using Driver 3)
void washStation3() {
  // Stage 1: Run Pump 5 only for 10 seconds
  Serial.println("Stage 1: Starting Pump 5 for 10 seconds");
  runMotor(IN9, IN10, ENABLE5, speedPWM_E);
  delay(PUMP_STAGE_TIME);
  stopMotor(IN9, IN10, ENABLE5);
  
  // Stage 2: Run Washer 3 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC motor for 60 seconds");
  runMotor(IN11, IN12, ENABLE6, speedPWM_I);
  delay(WASH_STAGE_TIME);
  stopMotor(IN11, IN12, ENABLE6);
  
  // Stage 3: Run Pump 6 (reverse) for 15 seconds
  Serial.println("Stage 3: Starting Pump 6 (reverse) for 15 seconds");
  runMotorReverse(IN9, IN10, ENABLE5, speedPWM_F);
  delay(RINSE_STAGE_TIME);
  stopMotor(IN9, IN10, ENABLE5);
  
  Serial.println("Wash Station 3 DONE - New Sequence Complete");
}

// Helper functions - Updated to use ENABLE pins directly
void runMotor(int in1, int in2, int enablePin, int speedPWM) {
  digitalWrite(in1, HIGH);
  digitalWrite(in2, LOW);
  ledcWrite(enablePin, speedPWM);
}

void runMotorReverse(int in1, int in2, int enablePin, int speedPWM) {
  digitalWrite(in1, LOW);
  digitalWrite(in2, HIGH);
  ledcWrite(enablePin, speedPWM);
}

void stopMotor(int in1, int in2, int enablePin) {
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  ledcWrite(enablePin, 0);
}

void stopAll() {
  // Stop all motors
  stopMotor(IN1, IN2, ENABLE1);
  stopMotor(IN3, IN4, ENABLE2);
  stopMotor(IN5, IN6, ENABLE3);
  stopMotor(IN7, IN8, ENABLE4);
  stopMotor(IN9, IN10, ENABLE5);
  stopMotor(IN11, IN12, ENABLE6);
  
  Serial.println("All Motors STOPPED");
}