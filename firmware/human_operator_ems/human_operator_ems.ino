// Electrode select lines (user-provided config)
const int electrode1 = 2;  // wrist_left
const int electrode2 = 4;  // wrist_right
const int electrode3 = 3;  // thumb
const int electrode4 = 5;  // index
const int electrode5 = 6;  // middle
const int electrode6 = 7;  // ring
const int electrode7 = 8;  // pinky

// Most relay boards are active-low (LOW = ON, HIGH = OFF).
// If your board is active-high, set this to false.
bool relayActiveLow = false;

const int relayPins[] = {electrode1, electrode2, electrode3, electrode4, electrode5, electrode6, electrode7};
const int relayPinCount = sizeof(relayPins) / sizeof(relayPins[0]);

int relayOnLevel() {
  return relayActiveLow ? LOW : HIGH;
}

int relayOffLevel() {
  return relayActiveLow ? HIGH : LOW;
}

void setRelayState(int pin, bool enabled) {
  digitalWrite(pin, enabled ? relayOnLevel() : relayOffLevel());
}

void allOff() {
  for (int i = 0; i < relayPinCount; i++) {
    setRelayState(relayPins[i], false);
  }
}

void selectOnly(int pin) {
  allOff();
  setRelayState(pin, true);
}

void runTestSweep() {
  Serial.println("Running relay sweep test...");
  for (int i = 0; i < relayPinCount; i++) {
    allOff();
    setRelayState(relayPins[i], true);
    Serial.print("Test ON pin D");
    Serial.println(relayPins[i]);
    delay(700);
  }
  allOff();
  Serial.println("Relay sweep done.");
}

bool isCommand(const String& command, const char* longName, char shortAlias) {
  return command.equalsIgnoreCase(longName) || (command.length() == 1 && tolower(command[0]) == shortAlias);
}

void setup() {
  // Initialize serial communication so we can chat with it
  Serial.begin(115200);

  // Initialize all electrode select pins as outputs
  pinMode(electrode1, OUTPUT);
  pinMode(electrode2, OUTPUT);
  pinMode(electrode3, OUTPUT);
  pinMode(electrode4, OUTPUT);
  pinMode(electrode5, OUTPUT);
  pinMode(electrode6, OUTPUT);
  pinMode(electrode7, OUTPUT);

  allOff();

  // Print the instructions to the Serial Monitor
  Serial.println("Electrode Router Ready.");
  Serial.println("Commands (name or alias):");
  Serial.println("wrist_left/w, wrist_right/q, thumb/t, index/i, middle/m, ring/r, pinky/p");
  Serial.println("x = all off, test = sweep channels");
  Serial.println("mode_low = active-low relays, mode_high = active-high relays");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.length() == 0) {
      return;
    }

    if (isCommand(command, "wrist_left", 'w')) {
      selectOnly(electrode1);
      Serial.println("Selected: wrist_left");
    } else if (isCommand(command, "wrist_right", 'q')) {
      selectOnly(electrode2);
      Serial.println("Selected: wrist_right");
    } else if (isCommand(command, "thumb", 't')) {
      selectOnly(electrode3);
      Serial.println("Selected: thumb");
    } else if (isCommand(command, "index", 'i')) {
      selectOnly(electrode4);
      Serial.println("Selected: index");
    } else if (isCommand(command, "middle", 'm')) {
      selectOnly(electrode5);
      Serial.println("Selected: middle");
    } else if (isCommand(command, "ring", 'r')) {
      selectOnly(electrode6);
      Serial.println("Selected: ring");
    } else if (isCommand(command, "pinky", 'p')) {
      selectOnly(electrode7);
      Serial.println("Selected: pinky");
    } else if (command.equalsIgnoreCase("x")) {
      allOff();
      Serial.println("All electrodes OFF");
    } else if (command.equalsIgnoreCase("test")) {
      runTestSweep();
    } else if (command.equalsIgnoreCase("mode_low")) {
      relayActiveLow = true;
      allOff();
      Serial.println("Relay polarity set to ACTIVE-LOW");
    } else if (command.equalsIgnoreCase("mode_high")) {
      relayActiveLow = false;
      allOff();
      Serial.println("Relay polarity set to ACTIVE-HIGH");
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }
  }
}