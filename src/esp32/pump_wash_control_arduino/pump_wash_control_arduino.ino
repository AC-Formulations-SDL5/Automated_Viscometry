// Enhanced Washing Station Control for CNC-Viscometer Orchestration
// USE Arduino IDE for running, testing and uploading the code.
// Supports individual component control for precise CNC coordination

#include <Arduino.h>

// Driver 1 (Pump 1, Motor 1)  - Wash Station 1
#define ENABLE1 25  // Pump 1 
#define IN1     27
#define IN2     14
#define ENABLE2 33  // Motor 1 (12V DC)
#define IN3     32 
#define IN4     23

// Driver 2 (Pump 3, Motor 2)  - Wash Station 2
#define ENABLE3 26  // Pump 3
#define IN5     13
#define IN6     12
#define ENABLE4 18  // Motor 2 (12V DC)
#define IN7     19
#define IN8     21

// Driver 3 (Pump 5, Motor 3)  - Wash Station 3 (Future)
#define ENABLE5 22  // Pump 5
#define IN9     5
#define IN10    17
#define ENABLE6 16  // Motor 3 (12V DC)
#define IN11    4
#define IN12    2

// PWM setup
const int pwmFreq = 1000;    // PWM frequency
const int pwmResolution = 8; // 8-bit resolution (0-255)

// Motor speeds - optimized for different components
const int speedPump1 = 170;  // Pump 1 (wash station 1 cleaning)
const int speedPump2 = 170;  // Pump 2 (wash station 1 rinse) - Uses Pump1 reverse
const int speedPump3 = 170;  // Pump 3 (wash station 2 cleaning)
const int speedPump4 = 170;  // Pump 4 (wash station 2 rinse) - Uses Pump3 reverse
const int speedPump5 = 210;  // Pump 5 (future use)
const int speedPump6 = 210;  // Pump 6 (future use)
const int speedMotor1 = 160; // 12V DC Motor 1 (wash station 1 agitation)
const int speedMotor2 = 160; // 12V DC Motor 2 (wash station 2 agitation)
const int speedMotor3 = 160; // 12V DC Motor 3 (future use)

// Component state tracking
bool pump1_running = false;
bool pump3_running = false;
bool pump5_running = false;
bool motor1_running = false;
bool motor2_running = false;
bool motor3_running = false;
bool reverse1_running = false;
bool reverse2_running = false;

// Legacy sequence timing (for backward compatibility)
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
  
  // Setup PWM channels using new ESP32 API
  ledcAttach(ENABLE1, pwmFreq, pwmResolution);
  ledcAttach(ENABLE2, pwmFreq, pwmResolution);
  ledcAttach(ENABLE3, pwmFreq, pwmResolution);
  ledcAttach(ENABLE4, pwmFreq, pwmResolution);
  ledcAttach(ENABLE5, pwmFreq, pwmResolution);
  ledcAttach(ENABLE6, pwmFreq, pwmResolution);
  
  Serial.begin(115200);
  Serial.println("Enhanced Washing Station Control v2.0");
  Serial.println("Individual Commands: P1,SP1,M1,SM1,R1,SR1,P3,SP3,M2,SM2,R2,SR2");
  Serial.println("Legacy Commands: 1,2,3 (full sequences), 0 (emergency stop)");
  Serial.println("Status Command: ST (get component states)");
}

// Enhanced main loop with individual component control
void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // Individual Component Control Commands
    if (command == "P1") {          // Start Pump 1
      startPump1();
    } else if (command == "SP1") {  // Stop Pump 1
      stopPump1();
    } else if (command == "P3") {   // Start Pump 3
      startPump3();
    } else if (command == "SP3") {  // Stop Pump 3
      stopPump3();
    } else if (command == "M1") {   // Start Motor 1
      startMotor1();
    } else if (command == "SM1") {  // Stop Motor 1
      stopMotor1();
    } else if (command == "M2") {   // Start Motor 2
      startMotor2();
    } else if (command == "SM2") {  // Stop Motor 2
      stopMotor2();
    } else if (command == "R1") {   // Start Reverse 1
      startReverse1();
    } else if (command == "SR1") {  // Stop Reverse 1
      stopReverse1();
    } else if (command == "R2") {   // Start Reverse 2
      startReverse2();
    } else if (command == "SR2") {  // Stop Reverse 2
      stopReverse2();
    } else if (command == "ST") {   // Status request
      printStatus();
      
    // Legacy sequence commands (backward compatibility)
    } else if (command == "1") {
      Serial.println("Starting Legacy Wash Station 1 Sequence...");
      washStation1();
    } else if (command == "2") {
      Serial.println("Starting Legacy Wash Station 2 Sequence...");
      washStation2();
    } else if (command == "3") {
      Serial.println("Starting Legacy Wash Station 3 Sequence...");
      washStation3();
    } else if (command == "0") {
      Serial.println("EMERGENCY STOP - All components stopping!");
      stopAll();
    } else {
      Serial.println("Unknown command: " + command);
      Serial.println("Valid commands: P1,SP1,M1,SM1,R1,SR1,P3,SP3,M2,SM2,R2,SR2,ST,1,2,3,0");
    }
  }
}

// Individual Component Control Functions

// Pump 1 (Wash Station 1 cleaning)
void startPump1() {
  if (!pump1_running && !reverse1_running) {
    runMotor(IN1, IN2, ENABLE1, speedPump1);
    pump1_running = true;
    Serial.println("Pump 1 STARTED");
  } else {
    Serial.println("ERROR: Pump 1 conflict - check reverse/pump state");
  }
}

void stopPump1() {
  stopMotor(IN1, IN2, ENABLE1);
  pump1_running = false;
  Serial.println("Pump 1 STOPPED");
}

// Pump 3 (Wash Station 2 cleaning)
void startPump3() {
  if (!pump3_running && !reverse2_running) {
    runMotor(IN5, IN6, ENABLE3, speedPump3);
    pump3_running = true;
    Serial.println("Pump 3 STARTED");
  } else {
    Serial.println("ERROR: Pump 3 conflict - check reverse/pump state");
  }
}

void stopPump3() {
  stopMotor(IN5, IN6, ENABLE3);
  pump3_running = false;
  Serial.println("Pump 3 STOPPED");
}

// Motor 1 (12V DC Motor Wash Station 1)
void startMotor1() {
  if (!motor1_running) {
    runMotor(IN3, IN4, ENABLE2, speedMotor1);
    motor1_running = true;
    Serial.println("Motor 1 STARTED (12V DC)");
  } else {
    Serial.println("ERROR: Motor 1 already running");
  }
}

void stopMotor1() {
  stopMotor(IN3, IN4, ENABLE2);
  motor1_running = false;
  Serial.println("Motor 1 STOPPED");
}

// Motor 2 (12V DC Motor Wash Station 2)
void startMotor2() {
  if (!motor2_running) {
    runMotor(IN7, IN8, ENABLE4, speedMotor2);
    motor2_running = true;
    Serial.println("Motor 2 STARTED (12V DC)");
  } else {
    Serial.println("ERROR: Motor 2 already running");
  }
}

void stopMotor2() {
  stopMotor(IN7, IN8, ENABLE4);
  motor2_running = false;
  Serial.println("Motor 2 STOPPED");
}

// Reverse 1 (Pump 2 functionality - reverse direction of Pump 1)
void startReverse1() {
  if (!reverse1_running && !pump1_running) {
    runMotorReverse(IN1, IN2, ENABLE1, speedPump2);
    reverse1_running = true;
    Serial.println("Reverse 1 STARTED (Rinse Station 1)");
  } else {
    Serial.println("ERROR: Reverse 1 conflict - check pump/reverse state");
  }
}

void stopReverse1() {
  stopMotor(IN1, IN2, ENABLE1);
  reverse1_running = false;
  Serial.println("Reverse 1 STOPPED");
}

// Reverse 2 (Pump 4 functionality - reverse direction of Pump 3)
void startReverse2() {
  if (!reverse2_running && !pump3_running) {
    runMotorReverse(IN5, IN6, ENABLE3, speedPump4);
    reverse2_running = true;
    Serial.println("Reverse 2 STARTED (Rinse Station 2)");
  } else {
    Serial.println("ERROR: Reverse 2 conflict - check pump/reverse state");
  }
}

void stopReverse2() {
  stopMotor(IN5, IN6, ENABLE3);
  reverse2_running = false;
  Serial.println("Reverse 2 STOPPED");
}

// Status reporting
void printStatus() {
  Serial.println("=== COMPONENT STATUS ===");
  Serial.println("Pump 1: " + String(pump1_running ? "RUNNING" : "STOPPED"));
  Serial.println("Pump 3: " + String(pump3_running ? "RUNNING" : "STOPPED"));
  Serial.println("Motor 1: " + String(motor1_running ? "RUNNING" : "STOPPED"));
  Serial.println("Motor 2: " + String(motor2_running ? "RUNNING" : "STOPPED"));
  Serial.println("Reverse 1: " + String(reverse1_running ? "RUNNING" : "STOPPED"));
  Serial.println("Reverse 2: " + String(reverse2_running ? "RUNNING" : "STOPPED"));
  Serial.println("========================");
}

// Legacy sequence functions (for backward compatibility)

// Wash Station 1: Pump 1 → Motor 1 → Reverse 1
void washStation1() {
  Serial.println("=== WASH STATION 1 LEGACY SEQUENCE ===");
  
  // Stage 1: Run Pump 1 for 10 seconds
  Serial.println("Stage 1: Starting Pump 1 for 10 seconds");
  startPump1();
  delay(PUMP_STAGE_TIME);
  stopPump1();
  
  // Stage 2: Run Motor 1 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC Motor 1 for 60 seconds");
  startMotor1();
  delay(WASH_STAGE_TIME);
  stopMotor1();
  
  // Stage 3: Run Reverse 1 for 15 seconds
  Serial.println("Stage 3: Starting Reverse 1 (rinse) for 15 seconds");
  startReverse1();
  delay(RINSE_STAGE_TIME);
  stopReverse1();
  
  Serial.println("Wash Station 1 Legacy Sequence COMPLETE");
}

// Wash Station 2: Pump 3 → Motor 2 → Reverse 2  
void washStation2() {
  Serial.println("=== WASH STATION 2 LEGACY SEQUENCE ===");
  
  // Stage 1: Run Pump 3 for 10 seconds
  Serial.println("Stage 1: Starting Pump 3 for 10 seconds");
  startPump3();
  delay(PUMP_STAGE_TIME);
  stopPump3();
  
  // Stage 2: Run Motor 2 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC Motor 2 for 60 seconds");
  startMotor2();
  delay(WASH_STAGE_TIME);
  stopMotor2();
  
  // Stage 3: Run Reverse 2 for 15 seconds
  Serial.println("Stage 3: Starting Reverse 2 (rinse) for 15 seconds");
  startReverse2();
  delay(RINSE_STAGE_TIME);
  stopReverse2();
  
  Serial.println("Wash Station 2 Legacy Sequence COMPLETE");
}

// Wash Station 3: Future expansion (Pump 5 → Motor 3 → Pump 6)
void washStation3() {
  Serial.println("=== WASH STATION 3 LEGACY SEQUENCE ===");
  
  // Stage 1: Run Pump 5 for 10 seconds
  Serial.println("Stage 1: Starting Pump 5 for 10 seconds");
  if (!pump5_running) {
    runMotor(IN9, IN10, ENABLE5, speedPump5);
    pump5_running = true;
    Serial.println("Pump 5 STARTED");
  }
  delay(PUMP_STAGE_TIME);
  stopMotor(IN9, IN10, ENABLE5);
  pump5_running = false;
  Serial.println("Pump 5 STOPPED");
  
  // Stage 2: Run Motor 3 (12V DC motor) for 60 seconds  
  Serial.println("Stage 2: Starting 12V DC Motor 3 for 60 seconds");
  if (!motor3_running) {
    runMotor(IN11, IN12, ENABLE6, speedMotor3);
    motor3_running = true;
    Serial.println("Motor 3 STARTED");
  }
  delay(WASH_STAGE_TIME);
  stopMotor(IN11, IN12, ENABLE6);
  motor3_running = false;
  Serial.println("Motor 3 STOPPED");
  
  // Stage 3: Run Pump 6 (reverse) for 15 seconds
  Serial.println("Stage 3: Starting Pump 6 (reverse) for 15 seconds");
  runMotorReverse(IN9, IN10, ENABLE5, speedPump6);
  delay(RINSE_STAGE_TIME);
  stopMotor(IN9, IN10, ENABLE5);
  
  Serial.println("Wash Station 3 Legacy Sequence COMPLETE");
}

// Low-level motor control helper functions
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

// Emergency stop all components
void stopAll() {
  // Stop all motors and reset state tracking
  stopMotor(IN1, IN2, ENABLE1);   // Pump 1 / Reverse 1
  stopMotor(IN3, IN4, ENABLE2);   // Motor 1
  stopMotor(IN5, IN6, ENABLE3);   // Pump 3 / Reverse 2
  stopMotor(IN7, IN8, ENABLE4);   // Motor 2
  stopMotor(IN9, IN10, ENABLE5);  // Pump 5 / Pump 6
  stopMotor(IN11, IN12, ENABLE6); // Motor 3
  
  // Reset all state flags
  pump1_running = false;
  pump3_running = false;
  pump5_running = false;
  motor1_running = false;
  motor2_running = false;
  motor3_running = false;
  reverse1_running = false;
  reverse2_running = false;
  
  Serial.println("EMERGENCY STOP: All motors and pumps STOPPED");
  Serial.println("All component states RESET");
}