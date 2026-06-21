// Electrode relay router.
//
// A single stimulator channel (channel 2) is routed through this relay board to
// one of three electrodes. Only one relay is active at a time, so the three
// actions are mutually exclusive.
const int electrode1 = 2;  // wrist_left
const int electrode2 = 4;  // wrist_right
const int electrode3 = 3;  // grab (grip)

// Most relay boards are active-low (LOW = ON, HIGH = OFF).
// If your board is active-high, set this to false.
bool relayActiveLow = false;

const int relayPins[] = {electrode1, electrode2, electrode3};
const int relayPinCount = sizeof(relayPins) / sizeof(relayPins[0]);

// Auto-off safety. If the stimulator runs continuously, the relay hold time IS
// the stimulation time. A selected electrode is dropped when its hold expires,
// so it can never get stuck on if commands stop arriving.
// holdUntil == 0 means nothing is scheduled.
unsigned long holdUntil = 0;
const unsigned long DEFAULT_HOLD_MS = 2000;  // fallback if a select passes 0
const unsigned long MAX_HOLD_MS = 5000;      // hard cap so nothing sticks on too long

// Per-action hold times. The firmware owns these; the host just sends the name.
const unsigned long GRAB_HOLD_MS = 2000;     // grip holds long enough to grab
const unsigned long WRIST_HOLD_MS = 300;     // a wrist turn is a quick flick

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

void select(int pin, unsigned long holdMs) {
  if (holdMs == 0) holdMs = DEFAULT_HOLD_MS;
  if (holdMs > MAX_HOLD_MS) holdMs = MAX_HOLD_MS;
  allOff();
  setRelayState(pin, true);
  holdUntil = millis() + holdMs;
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

  // Initialize the electrode select pins as outputs
  pinMode(electrode1, OUTPUT);
  pinMode(electrode2, OUTPUT);
  pinMode(electrode3, OUTPUT);

  allOff();

  // Print the instructions to the Serial Monitor
  Serial.println("Electrode Relay Router Ready.");
  Serial.println("Commands (name or alias):");
  Serial.println("wrist_left/w, wrist_right/q, grab/g");
  Serial.println("x = all off, test = sweep channels");
  Serial.println("mode_low = active-low relays, mode_high = active-high relays");
}

void loop() {
  // Safety watchdog: drop the active electrode once its hold time expires.
  // (long) cast handles millis() rollover correctly.
  if (holdUntil != 0 && (long)(millis() - holdUntil) >= 0) {
    allOff();
    holdUntil = 0;
    Serial.println("Auto-off (hold expired)");
  }

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.length() == 0) {
      return;
    }

    if (isCommand(command, "wrist_left", 'w')) {
      select(electrode1, WRIST_HOLD_MS);
      Serial.println("Selected: wrist_left");
    } else if (isCommand(command, "wrist_right", 'q')) {
      select(electrode2, WRIST_HOLD_MS);
      Serial.println("Selected: wrist_right");
    } else if (isCommand(command, "grab", 'g')) {
      select(electrode3, GRAB_HOLD_MS);
      Serial.println("Selected: grab");
    } else if (command.equalsIgnoreCase("x")) {
      allOff();
      holdUntil = 0;
      Serial.println("All electrodes OFF");
    } else if (command.equalsIgnoreCase("test")) {
      runTestSweep();
    } else if (command.equalsIgnoreCase("mode_low")) {
      relayActiveLow = true;
      allOff();
      holdUntil = 0;
      Serial.println("Relay polarity set to ACTIVE-LOW");
    } else if (command.equalsIgnoreCase("mode_high")) {
      relayActiveLow = false;
      allOff();
      holdUntil = 0;
      Serial.println("Relay polarity set to ACTIVE-HIGH");
    } else {
      Serial.print("Unknown command: ");
      Serial.println(command);
    }
  }
}
