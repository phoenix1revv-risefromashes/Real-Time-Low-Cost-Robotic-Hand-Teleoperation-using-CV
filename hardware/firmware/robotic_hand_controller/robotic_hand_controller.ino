/*
 * Vision-guided robotic hand: Arduino UNO control firmware, v0.1.
 * Host protocol: @0001:MOVE:90,90,90,90,90*XX\n (XOR checksum).
 * Wiring: five servo signal lines D9-D13; NC E-stop switch D2-to-GND.
 * With NC switch open, PWM is disabled. A SEPARATE hardwired switch must
 * remove servo power for a physical emergency stop.
 *
 * Does NOT implement torque limiting, joint feedback or functional safety.
 * Use a separate regulated servo power supply (common signal ground).
 */
#include <Arduino.h>
#include <Servo.h>
#include <stdlib.h>
#include <string.h>

constexpr uint8_t NUM_SERVOS = 5;
constexpr uint8_t SERVO_PINS[NUM_SERVOS] = {9, 10, 11, 12, 13};
constexpr uint8_t ESTOP_PIN = 2;  // Normally-closed to GND -> LOW means permitted.
constexpr int SERVO_MIN[NUM_SERVOS] = {30, 30, 30, 30, 30};
constexpr int SERVO_MAX[NUM_SERVOS] = {130, 130, 130, 130, 130};
constexpr int HOME_DEG = 90;
constexpr int MAX_COMMAND_STEP_DEG = 15;  // Additional software slew bound.
constexpr unsigned long WATCHDOG_MS = 450;
constexpr size_t BUFFER_SIZE = 96;

Servo servos[NUM_SERVOS];
int lastAngles[NUM_SERVOS] = {90, 90, 90, 90, 90};
char lineBuffer[BUFFER_SIZE];
size_t lineLength = 0;
bool overflow = false;
bool active = false;
unsigned long lastHeartbeatMs = 0;

bool interlockIsClosed() { return digitalRead(ESTOP_PIN) == LOW; }

void stopServos() {
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    if (servos[i].attached()) servos[i].detach();
  }
  active = false;
  // Mirrors host virtual-home after STOP. This does not physically home joints.
  for (uint8_t i = 0; i < NUM_SERVOS; i++) lastAngles[i] = HOME_DEG;
}

uint8_t xorChecksum(const char *start) {
  uint8_t value = 0;
  while (*start != '\0') value ^= static_cast<uint8_t>(*start++);
  return value;
}

int hexDigit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

void reply(const char *sequence, const char *verb, const char *reason = nullptr) {
  char body[64];
  if (reason != nullptr) {
    snprintf(body, sizeof(body), "%s:%s:%s", sequence, verb, reason);
  } else {
    snprintf(body, sizeof(body), "%s:%s", sequence, verb);
  }
  Serial.print('@');
  Serial.print(body);
  Serial.print('*');
  uint8_t sum = xorChecksum(body);
  if (sum < 16) Serial.print('0');
  Serial.println(sum, HEX);
}

bool parseAngles(char *text, int out[NUM_SERVOS]) {
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    if (*text == '\0') return false;
    char *end = nullptr;
    long value = strtol(text, &end, 10);
    if (end == text || value < SERVO_MIN[i] || value > SERVO_MAX[i]) return false;
    out[i] = static_cast<int>(value);
    if (i == NUM_SERVOS - 1) return *end == '\0';
    if (*end != ',') return false;
    text = end + 1;
  }
  return false;
}

void processLine(char *line) {
  // Invalid frames never move the motors; no side effects before validation.
  if (line[0] != '@') return;
  char *star = strchr(line + 1, '*');
  if (star == nullptr || strlen(star + 1) != 2) return;
  int upper = hexDigit(star[1]);
  int lower = hexDigit(star[2]);
  if (upper < 0 || lower < 0) return;
  *star = '\0';
  if (xorChecksum(line + 1) != static_cast<uint8_t>((upper << 4) | lower)) return;

  char *sep = strchr(line + 1, ':');
  if (sep == nullptr) return;
  *sep = '\0';
  const char *sequence = line + 1;
  if (strlen(sequence) != 4) return;
  for (uint8_t i = 0; i < 4; i++) {
    if (sequence[i] < '0' || sequence[i] > '9') return;
  }
  char *verb = sep + 1;
  char *data = strchr(verb, ':');
  if (data != nullptr) {
    *data = '\0';
    ++data;
  }

  if (strcmp(verb, "STOP") == 0 && data == nullptr) {
    stopServos();
    reply(sequence, "OK");
    return;
  }
  if (strcmp(verb, "PING") == 0 && data == nullptr) {
    if (active && interlockIsClosed()) lastHeartbeatMs = millis();
    reply(sequence, "OK");
    return;
  }
  if (strcmp(verb, "MOVE") != 0 || data == nullptr) {
    reply(sequence, "ERR", "FORMAT");
    return;
  }
  if (!interlockIsClosed()) {
    stopServos();
    reply(sequence, "ERR", "ESTOP");
    return;
  }
  int nextAngles[NUM_SERVOS];
  if (!parseAngles(data, nextAngles)) {
    reply(sequence, "ERR", "LIMITS");
    return;
  }
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    int diff = abs(nextAngles[i] - lastAngles[i]);
    if (diff > MAX_COMMAND_STEP_DEG) {
      reply(sequence, "ERR", "SLEW");
      return;
    }
  }
  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    if (!servos[i].attached()) {
      // Motors may jump to this setpoint on initial attach. Bench-calibrate
      // the physical home angle BEFORE energizing and clear all pinch points.
      servos[i].write(HOME_DEG);
      servos[i].attach(SERVO_PINS[i]);
    }
    servos[i].write(nextAngles[i]);
    lastAngles[i] = nextAngles[i];
  }
  active = true;
  lastHeartbeatMs = millis();
  reply(sequence, "OK");
}

void setup() {
  pinMode(ESTOP_PIN, INPUT_PULLUP);
  Serial.begin(115200);
  stopServos();
}

void loop() {
  // Interlock and watchdog are checked independent of incoming host data.
  if (!interlockIsClosed() || (active && millis() - lastHeartbeatMs > WATCHDOG_MS)) {
    stopServos();
  }
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      if (!overflow && lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        processLine(lineBuffer);
      }
      lineLength = 0;
      overflow = false;
    } else if (!overflow) {
      if (lineLength + 1 < BUFFER_SIZE) {
        lineBuffer[lineLength++] = c;
      } else {
        overflow = true;
      }
    }
  }
}
