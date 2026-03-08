// Define the pins connected to the relays
const int pinkyRelay = 10; 
const int middleRelay = 16; 
const int indexRelay = 15; 

void setup() {
  // Initialize serial communication so we can chat with it
  Serial.begin(115200);

  // Initialize all the relay pins as outputs
  pinMode(pinkyRelay, OUTPUT);
  pinMode(middleRelay, OUTPUT);
  pinMode(indexRelay, OUTPUT);

  // Set them all to LOW (OFF) to start clean
  digitalWrite(pinkyRelay, LOW);
  digitalWrite(middleRelay, LOW);
  digitalWrite(indexRelay, LOW);

  // Print the instructions to the Serial Monitor
  Serial.println("Relay Vibe Check: Ready.");
  Serial.println("Type 'p' for Pinky, 'm' for Middle, 'i' for Index.");
  Serial.println("Type 'x' to turn all off.");
}

void loop() {
  // Check if we typed anything in the Serial Monitor
  if (Serial.available() > 0) {
    // Read the incoming character
    char command = Serial.read();

    // Handle the command
    switch (command) {
      case 'p':
        // Toggle the pinky relay (flips it to the opposite of its current state)
        digitalWrite(pinkyRelay, !digitalRead(pinkyRelay)); 
        Serial.print("Pinky Relay is now: ");
        Serial.println(digitalRead(pinkyRelay) ? "ON" : "OFF");
        break;

      case 'm':
        digitalWrite(middleRelay, !digitalRead(middleRelay)); 
        Serial.print("Middle Relay is now: ");
        Serial.println(digitalRead(middleRelay) ? "ON" : "OFF");
        break;

      case 'i':
        digitalWrite(indexRelay, !digitalRead(indexRelay)); 
        Serial.print("Index Relay is now: ");
        Serial.println(digitalRead(indexRelay) ? "ON" : "OFF");
        break;

          case 'x':
        // Turn everything off
        digitalWrite(pinkyRelay, LOW);
        digitalWrite(middleRelay, LOW);
        digitalWrite(indexRelay, LOW);
        Serial.println("All Relays OFF. Chilling.");
        break;

      // Ignore carriage returns and newlines so they don't trigger the default case
      case '\n':
      case '\r':
        break;

      default:
        Serial.println("Unknown vibe. Stick to p, m, i, or x.");
        break;
    }
  }
}