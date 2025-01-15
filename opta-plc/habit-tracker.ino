#include <PubSubClient.h>

#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiSSLClient.h>
#include <WiFiServer.h>
#include <WiFiUdp.h>

#define pin_I1 A0
#define pin_I2 A1
#define pin_I3 A2
#define pin_I4 A3
#define pin_I5 A4
#define pin_I6 A5

// Wi-Fi credentials
const char* ssid = "--";
const char* password = "--";

//mqtt
const char* mqtt_username = "--"; //remove if no auth
const char* mqtt_password = "--"; //remove if no auth

const char* mqtt_topic = "opta/I1";

// MQTT broker static IP
IPAddress broker(0, 0, 0, 0);  // Replace with broker's static IP

WiFiClient wifiClient;
PubSubClient client(wifiClient);

// Relay input pins (adjust as needed for your setup)
const int relayPins[] = { pin_I1, pin_I2, pin_I3, pin_I4, pin_I5, pin_I6 };
const char* statuses[] = { "Time with God", "Time with Family", "Sleeping", "Working", "Learning", "Working Out" };

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  WiFi.begin(ssid, password);

  client.setServer(broker, 1883);
}

void loop() {
  if (!client.connected()) {
    client.connect("OptaClient", mqtt_username, mqtt_password);
    digitalWrite(LED_BUILTIN, HIGH);
  }

  client.loop();

  int pinValue = digitalRead(pin_I1);

  // Check if all relay pins are LOW
  bool allLow = true;
  for (int i = 0; i < 6; i++) {
    if (digitalRead(relayPins[i]) == HIGH) {  // If any pin is HIGH, allLow becomes false
      allLow = false;
      break;
    }
  }


  // Check the relay states and publish changes
  for (int i = 0; i < 6; i++) {
    if (digitalRead(relayPins[i]) == HIGH) {
      client.publish("opta/status", statuses[i]);
      break;
    }
  }

  // If all pins are LOW, publish the message
  if (allLow) {
    client.publish("opta/status", "");
  }

  // Publish the pin value to the MQTT topic
  char msg[10];
  snprintf(msg, sizeof(msg), "%d", pinValue);
  client.publish("opta/I1", msg);

  //wait 1 minute
  delay(10000);
}
