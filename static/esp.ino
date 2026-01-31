#include <WiFi.h>
#include <esp_now.h>

// =====================
// CONFIG
// =====================
const int LED_PIN = 2;

// Replace with other ESP32 MAC
uint8_t peerMAC[] = {0x84, 0xCC, 0xA8, 0x0F, 0x19, 0x20};

// =====================
// DATA STRUCTURE
// =====================
struct Packet {
  char text[100];
};

Packet outgoing;
Packet incoming;

// Stores last message (for "show")
char lastMessage[100] = "";

// =====================
// LED FLASH
// =====================
void flash() {
  digitalWrite(LED_PIN, HIGH);
  delay(120);
  digitalWrite(LED_PIN, LOW);
}

// =====================
// RECEIVE CALLBACK
// =====================
void onReceive(const esp_now_recv_info_t* info,
               const uint8_t* data,
               int len) {

  if (len != sizeof(Packet)) return;

  memcpy(&incoming, data, sizeof(Packet));

  // Save message
  strcpy(lastMessage, incoming.text);

  // FLASH ON RECEIVE
  flash();

  Serial.print("Received: ");
  Serial.println(lastMessage);
}

// =====================
// SEND CALLBACK (optional debug)
// =====================
void onSent(const uint8_t* mac, esp_now_send_status_t status) {
  // You can debug here if needed
}

// =====================
// SETUP
// =====================
void setup() {

  Serial.begin(115200);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Failed");
    while (true);
  }

  esp_now_register_recv_cb(onReceive);
  esp_now_register_send_cb(onSent);

  // Add peer
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, peerMAC, 6);

  peer.channel = 0;
  peer.encrypt = false;

  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("Failed to add peer");
    while (true);
  }

  Serial.println("Ready.");
  Serial.println("Type text to send.");
  Serial.println("Type 'show' to display last message.");
}

// =====================
// LOOP
// =====================
void loop() {

  if (!Serial.available()) return;

  String input = Serial.readStringUntil('\n');
  input.trim();

  if (input.length() == 0) return;


  // -------------------
  // SHOW (NO FLASH)
  // -------------------
  if (input.equalsIgnoreCase("show")) {

    Serial.print("Last message: ");
    Serial.println(lastMessage);
    Serial.println("----------------");

    return;
  }


  // -------------------
  // SEND MESSAGE
  // -------------------

  input.toCharArray(outgoing.text, 100);

  esp_now_send(peerMAC,
               (uint8_t*)&outgoing,
               sizeof(Packet));

  // Save locally
  strcpy(lastMessage, outgoing.text);

  // FLASH ON SEND
  flash();

  Serial.print("Sent: ");
  Serial.println(lastMessage);
}