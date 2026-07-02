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

// ESP32 LEDC channel assignments for PWM enable pins
const int PWM_CHANNEL1 = 0;
const int PWM_CHANNEL2 = 1;
const int PWM_CHANNEL3 = 2;
const int PWM_CHANNEL4 = 3;
const int PWM_CHANNEL5 = 4;
const int PWM_CHANNEL6 = 5;

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
  pinMode(ENABLE1, OUTPUT); pinMode(ENABLE2, OUTPUT);
  pinMode(ENABLE3, OUTPUT); pinMode(ENABLE4, OUTPUT);
  pinMode(ENABLE5, OUTPUT); pinMode(ENABLE6, OUTPUT);
  
  // Ensure all pins start LOW
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  digitalWrite(IN5, LOW); digitalWrite(IN6, LOW);
  digitalWrite(IN7, LOW); digitalWrite(IN8, LOW);
  digitalWrite(IN9, LOW); digitalWrite(IN10, LOW);
  digitalWrite(IN11, LOW); digitalWrite(IN12, LOW);
  digitalWrite(ENABLE1, LOW); digitalWrite(ENABLE2, LOW);
  digitalWrite(ENABLE3, LOW); digitalWrite(ENABLE4, LOW);
  digitalWrite(ENABLE5, LOW); digitalWrite(ENABLE6, LOW);
  
  // Setup PWM pins using ESP32 LEDC API
  ledcAttach(ENABLE1, pwmFreq, pwmResolution);
  ledcAttach(ENABLE2, pwmFreq, pwmResolution);
  ledcAttach(ENABLE3, pwmFreq, pwmResolution);
  ledcAttach(ENABLE4, pwmFreq, pwmResolution);
  ledcAttach(ENABLE5, pwmFreq, pwmResolution);
  ledcAttach(ENABLE6, pwmFreq, pwmResolution);
  
  // Initialize all PWM to 0 (motors stopped)
  ledcWrite(ENABLE1, 0);
  ledcWrite(ENABLE2, 0);
  ledcWrite(ENABLE3, 0);
  ledcWrite(ENABLE4, 0);
  ledcWrite(ENABLE5, 0);
  ledcWrite(ENABLE6, 0);
  
  // Explicitly initialize state variables
  pump1_running = false;
  pump3_running = false;
  pump5_running = false;
  motor1_running = false;
  motor2_running = false;
  motor3_running = false;
  reverse1_running = false;
  reverse2_running = false;
  
  Serial.begin(115200);
  delay(1000);  // Allow serial to initialize
  Serial.println("Enhanced Washing Station Control v2.1 - DEBUGGED");
  Serial.println("Individual Commands: P1,SP1,M1,SM1,R1,SR1,P3,SP3,M2,SM2,R2,SR2");
  Serial.println("Legacy Commands: 1,2,3 (full sequences), 0 (emergency stop)");
  Serial.println("Status Command: ST (get component states)");
  Serial.println("\\n=== SYSTEM INITIALIZED ===");
  printStatus();  // Show initial system state
}


// Enhanced main loop with individual component control
void loop() {
  if (Serial.available()) {
    String command = "";
    unsigned long start_time = millis();
    
    // Read command with timeout protection
    while (Serial.available() || (millis() - start_time < 100)) {
      if (Serial.available()) {
        char c = Serial.read();
        if (c == '\r' || c == '\n') {
          if (command.length() > 0) {
            break;  // Complete command received
          }
          continue;  // Skip empty lines
        }
        command += c;
        start_time = millis();  // Reset timeout
      }
      delay(1);  // Small delay to prevent excessive polling
    }
    
    command.trim();
    
    if (command.length() == 0) {
      return;
    }
    
    Serial.println("\\n--- Received command: '" + command + "' ---");

    // Individual Component Control Commands
    if (command == "P1") {          // Start Pump 1
      startPump1();
      Serial.println("ACK:P1");
    } else if (command == "SP1") {  // Stop Pump 1
      stopPump1();
      Serial.println("ACK:SP1");
    } else if (command == "P3") {   // Start Pump 3
      startPump3();
      Serial.println("ACK:P3");
    } else if (command == "SP3") {  // Stop Pump 3
      stopPump3();
      Serial.println("ACK:SP3");
    } else if (command == "M1") {   // Start Motor 1
      startMotor1();
      Serial.println("ACK:M1");
    } else if (command == "SM1") {  // Stop Motor 1
      stopMotor1();
      Serial.println("ACK:SM1");
    } else if (command == "M2") {   // Start Motor 2
      startMotor2();
      Serial.println("ACK:M2");
    } else if (command == "SM2") {  // Stop Motor 2
      stopMotor2();
      Serial.println("ACK:SM2");
    } else if (command == "R1") {   // Start Reverse 1
      startReverse1();
      Serial.println("ACK:R1");
    } else if (command == "SR1") {  // Stop Reverse 1
      stopReverse1();
      Serial.println("ACK:SR1");
    } else if (command == "R2") {   // Start Reverse 2
      startReverse2();
      Serial.println("ACK:R2");
    } else if (command == "SR2") {  // Stop Reverse 2
      stopReverse2();
      Serial.println("ACK:SR2");
    } else if (command == "ST") {   // Status request
      printStatus();
      Serial.println("ACK:ST");
      
    // Legacy sequence commands (backward compatibility)
    } else if (command == "1") {
      Serial.println("Starting Legacy Wash Station 1 Sequence...");
      washStation1();
      Serial.println("ACK:1");
    } else if (command == "2") {
      Serial.println("Starting Legacy Wash Station 2 Sequence...");
      washStation2();
      Serial.println("ACK:2");
    } else if (command == "3") {
      Serial.println("Starting Legacy Wash Station 3 Sequence...");
      washStation3();
      Serial.println("ACK:3");
    } else if (command == "0") {
      Serial.println("EMERGENCY STOP - All components stopping!");
      stopAll();
      Serial.println("ACK:0");
    } else {
      Serial.println("Unknown command: " + command);
      Serial.println("Valid commands: P1,SP1,M1,SM1,R1,SR1,P3,SP3,M2,SM2,R2,SR2,ST,1,2,3,0");
    }
  }
}

// Individual Component Control Functions

// Pump 1 (Wash Station 1 cleaning)
void startPump1() {
  Serial.println("DEBUG: startPump1() called");
  Serial.println("State check - pump1_running: " + String(pump1_running) + ", reverse1_running: " + String(reverse1_running));
  
  if (!pump1_running && !reverse1_running) {
    runMotor(IN1, IN2, ENABLE1, speedPump1);
    pump1_running = true;
    Serial.println("SUCCESS: Pump 1 STARTED at speed " + String(speedPump1));
  } else {
    Serial.println("ERROR: Pump 1 conflict - pump1: " + String(pump1_running) + ", reverse1: " + String(reverse1_running));
  }
}

void stopPump1() {
  Serial.println("DEBUG: stopPump1() called");
  stopMotor(IN1, IN2, ENABLE1);
  pump1_running = false;
  Serial.println("SUCCESS: Pump 1 STOPPED");
}

// Pump 3 (Wash Station 2 cleaning)
void startPump3() {
  Serial.println("DEBUG: startPump3() called");
  Serial.println("State check - pump3_running: " + String(pump3_running) + ", reverse2_running: " + String(reverse2_running));
  
  if (!pump3_running && !reverse2_running) {
    runMotor(IN5, IN6, ENABLE3, speedPump3);
    pump3_running = true;
    Serial.println("SUCCESS: Pump 3 STARTED at speed " + String(speedPump3));
  } else {
    Serial.println("ERROR: Pump 3 conflict - pump3: " + String(pump3_running) + ", reverse2: " + String(reverse2_running));
  }
}

void stopPump3() {
  Serial.println("DEBUG: stopPump3() called");
  stopMotor(IN5, IN6, ENABLE3);
  pump3_running = false;
  Serial.println("SUCCESS: Pump 3 STOPPED");
}

// Motor 1 (12V DC Motor Wash Station 1)
void startMotor1() {
  Serial.println("DEBUG: startMotor1() called");
  Serial.println("State check - motor1_running: " + String(motor1_running));
  
  if (!motor1_running) {
    runMotor(IN3, IN4, ENABLE2, speedMotor1);
    motor1_running = true;
    Serial.println("SUCCESS: Motor 1 STARTED (12V DC) at speed " + String(speedMotor1));
  } else {
    Serial.println("ERROR: Motor 1 already running");
  }
}

void stopMotor1() {
  Serial.println("DEBUG: stopMotor1() called");
  stopMotor(IN3, IN4, ENABLE2);
  motor1_running = false;
  Serial.println("SUCCESS: Motor 1 STOPPED");
}

// Motor 2 (12V DC Motor Wash Station 2)
void startMotor2() {
  Serial.println("DEBUG: startMotor2() called");
  Serial.println("State check - motor2_running: " + String(motor2_running));
  
  if (!motor2_running) {
    runMotor(IN7, IN8, ENABLE4, speedMotor2);
    motor2_running = true;
    Serial.println("SUCCESS: Motor 2 STARTED (12V DC) at speed " + String(speedMotor2));
  } else {
    Serial.println("ERROR: Motor 2 already running");
  }
}

void stopMotor2() {
  Serial.println("DEBUG: stopMotor2() called");
  stopMotor(IN7, IN8, ENABLE4);
  motor2_running = false;
  Serial.println("SUCCESS: Motor 2 STOPPED");
}

// Reverse 1 (Pump 2 functionality - reverse direction of Pump 1)
void startReverse1() {
  Serial.println("DEBUG: startReverse1() called");
  Serial.println("State check - reverse1_running: " + String(reverse1_running) + ", pump1_running: " + String(pump1_running));
  
  if (!reverse1_running && !pump1_running) {
    runMotorReverse(IN1, IN2, ENABLE1, speedPump2);
    reverse1_running = true;
    Serial.println("SUCCESS: Reverse 1 STARTED (Rinse Station 1) at speed " + String(speedPump2));
  } else {
    Serial.println("ERROR: Reverse 1 conflict - reverse1: " + String(reverse1_running) + ", pump1: " + String(pump1_running));
  }
}

void stopReverse1() {
  Serial.println("DEBUG: stopReverse1() called");
  stopMotor(IN1, IN2, ENABLE1);
  reverse1_running = false;
  Serial.println("SUCCESS: Reverse 1 STOPPED");
}

// Reverse 2 (Pump 4 functionality - reverse direction of Pump 3)
void startReverse2() {
  Serial.println("DEBUG: startReverse2() called");
  Serial.println("State check - reverse2_running: " + String(reverse2_running) + ", pump3_running: " + String(pump3_running));
  
  if (!reverse2_running && !pump3_running) {
    runMotorReverse(IN5, IN6, ENABLE3, speedPump4);
    reverse2_running = true;
    Serial.println("SUCCESS: Reverse 2 STARTED (Rinse Station 2) at speed " + String(speedPump4));
  } else {
    Serial.println("ERROR: Reverse 2 conflict - reverse2: " + String(reverse2_running) + ", pump3: " + String(pump3_running));
  }
}

void stopReverse2() {
  Serial.println("DEBUG: stopReverse2() called");
  stopMotor(IN5, IN6, ENABLE3);
  reverse2_running = false;
  Serial.println("SUCCESS: Reverse 2 STOPPED");
}

// Status reporting with enhanced debugging
void printStatus() {
  Serial.println("\\n=== COMPONENT STATUS REPORT ===");
  Serial.println("Wash Station 1:");
  Serial.println("  Pump 1: " + String(pump1_running ? "RUNNING" : "STOPPED"));
  Serial.println("  Motor 1: " + String(motor1_running ? "RUNNING" : "STOPPED"));
  Serial.println("  Reverse 1: " + String(reverse1_running ? "RUNNING" : "STOPPED"));
  Serial.println("Wash Station 2:");
  Serial.println("  Pump 3: " + String(pump3_running ? "RUNNING" : "STOPPED"));
  Serial.println("  Motor 2: " + String(motor2_running ? "RUNNING" : "STOPPED"));
  Serial.println("  Reverse 2: " + String(reverse2_running ? "RUNNING" : "STOPPED"));
  Serial.println("Future Use:");
  Serial.println("  Pump 5: " + String(pump5_running ? "RUNNING" : "STOPPED"));
  Serial.println("  Motor 3: " + String(motor3_running ? "RUNNING" : "STOPPED"));
  Serial.println("\\nTiming Constants:");
  Serial.println("  Pump Stage: " + String(PUMP_STAGE_TIME/1000) + " seconds");
  Serial.println("  Wash Stage: " + String(WASH_STAGE_TIME/1000) + " seconds");
  Serial.println("  Rinse Stage: " + String(RINSE_STAGE_TIME/1000) + " seconds");
  Serial.println("================================\\n");
}

// Legacy sequence functions (for backward compatibility)

// Wash Station 1: Pump 1 → Motor 1 → Reverse 1
void washStation1() {
  Serial.println("\n=== WASH STATION 1 LEGACY SEQUENCE START ===");
  printStatus();  // Show initial state
  
  // Stage 1: Run Pump 1 for 10 seconds
  Serial.println("\n--- Stage 1: Starting Pump 1 for " + String(PUMP_STAGE_TIME/1000) + " seconds ---");
  startPump1();
  if (pump1_running) {
    Serial.println("Pump 1 running for " + String(PUMP_STAGE_TIME/1000) + " seconds...");
    delay(PUMP_STAGE_TIME);
    stopPump1();
  } else {
    Serial.println("ERROR: Pump 1 failed to start, skipping stage 1");
  }
  
  // Stage 2: Run Motor 1 (12V DC motor) for 60 seconds  
  Serial.println("\n--- Stage 2: Starting 12V DC Motor 1 for " + String(WASH_STAGE_TIME/1000) + " seconds ---");
  startMotor1();
  if (motor1_running) {
    Serial.println("Motor 1 washing for " + String(WASH_STAGE_TIME/1000) + " seconds...");
    delay(WASH_STAGE_TIME);
    stopMotor1();
  } else {
    Serial.println("ERROR: Motor 1 failed to start, skipping stage 2");
  }
  
  // Stage 3: Run Reverse 1 for 15 seconds
  Serial.println("\n--- Stage 3: Starting Reverse 1 (rinse) for " + String(RINSE_STAGE_TIME/1000) + " seconds ---");
  startReverse1();
  if (reverse1_running) {
    Serial.println("Reverse rinse for " + String(RINSE_STAGE_TIME/1000) + " seconds...");
    delay(RINSE_STAGE_TIME);
    stopReverse1();
  } else {
    Serial.println("ERROR: Reverse 1 failed to start, skipping stage 3");
  }
  
  Serial.println("\n=== WASH STATION 1 LEGACY SEQUENCE COMPLETE ===");
  printStatus();  // Show final state
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

// Low-level motor control helper functions with debugging
void runMotor(int in1, int in2, int enablePin, int speedPWM) {
  Serial.println("DEBUG: runMotor() called - IN1=" + String(in1) + ", IN2=" + String(in2) + ", EnablePin=" + String(enablePin) + ", Speed=" + String(speedPWM));
  digitalWrite(in1, HIGH);
  digitalWrite(in2, LOW);
  ledcWrite(enablePin, speedPWM);
  Serial.println("DEBUG: Motor pins set - IN1=HIGH, IN2=LOW, PWM=" + String(speedPWM));
}

void runMotorReverse(int in1, int in2, int enablePin, int speedPWM) {
  Serial.println("DEBUG: runMotorReverse() called - IN1=" + String(in1) + ", IN2=" + String(in2) + ", EnablePin=" + String(enablePin) + ", Speed=" + String(speedPWM));
  digitalWrite(in1, LOW);
  digitalWrite(in2, HIGH);
  ledcWrite(enablePin, speedPWM);
  Serial.println("DEBUG: Motor pins set - IN1=LOW, IN2=HIGH, PWM=" + String(speedPWM));
}

void stopMotor(int in1, int in2, int enablePin) {
  Serial.println("DEBUG: stopMotor() called - IN1=" + String(in1) + ", IN2=" + String(in2) + ", EnablePin=" + String(enablePin));
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  ledcWrite(enablePin, 0);
  digitalWrite(enablePin, LOW);
  Serial.println("DEBUG: Motor stopped - IN1=LOW, IN2=LOW, PWM=0, ENABLE=LOW");
}

// Emergency stop all components
void stopAll() {
  Serial.println("\n=== EMERGENCY STOP ALL COMPONENTS ===");
  
  // Stop all motors with individual debugging
  Serial.println("Stopping Pump 1 / Reverse 1...");
  stopMotor(IN1, IN2, ENABLE1);   // Pump 1 / Reverse 1
  
  Serial.println("Stopping Motor 1...");
  stopMotor(IN3, IN4, ENABLE2);   // Motor 1
  
  Serial.println("Stopping Pump 3 / Reverse 2...");
  stopMotor(IN5, IN6, ENABLE3);   // Pump 3 / Reverse 2
  
  Serial.println("Stopping Motor 2...");
  stopMotor(IN7, IN8, ENABLE4);   // Motor 2
  
  Serial.println("Stopping Pump 5 / Pump 6...");
  stopMotor(IN9, IN10, ENABLE5);  // Pump 5 / Pump 6
  
  Serial.println("Stopping Motor 3...");
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
  
  Serial.println("EMERGENCY STOP COMPLETE: All motors and pumps STOPPED");
  Serial.println("All component states RESET");
  printStatus();
}