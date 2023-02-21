#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiManager.h>

const char* mqtt_server = "YOUR_IP_ADDRESS";
const int mqttPort = 1488;

const char* mqtt_user = "USERNAME"; 
const char* mqtt_pass = "PASSWORD";

WiFiClient espClient;

PubSubClient client(mqtt_server, mqttPort, espClient);


const int doorSwitch = 4;


const char* will_topic = "/online/bedroom";
const int will_qos = 2;
const bool will_retain = true;
const char* will_message = "offline";

const int interval = 1500;

bool stateChanged = false;

bool state;
String doorState;

IRAM_ATTR void changeDoorStatus(){
  Serial.println("Door State Has Changed");
  stateChanged = true;
}

void led_blink(int cnt){
  for(int i = 0; i < cnt; i++){
    digitalWrite(2, LOW);   // Turn the LED on by making the voltage LOW
    delay(500);            // Wait for a second
    digitalWrite(2, HIGH);  // Turn the LED off by making the voltage HIGH
    delay(500);            // Wait for a second
  }
  delay(2000);
}


void setup() {
  Serial.begin(9600);
  pinMode(doorSwitch, INPUT_PULLUP);
  state = digitalRead(doorSwitch);
  Serial.println("System Started!");
  attachInterrupt(digitalPinToInterrupt(doorSwitch), changeDoorStatus, CHANGE);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  WiFiManager wifiManager;
  wifiManager.autoConnect("AutoConnectAP");
  Serial.println("connected to AP");
  client.setServer(mqtt_server, mqttPort);
  while(!client.connected()){
    Serial.println("Connecting to MQTT Service...");
    if(client.connect("Bedroom", mqtt_user, mqtt_pass, will_topic, will_qos, will_retain, will_message)){
      led_blink(2);
      client.subscribe("Door_Sensor_1");
      Serial.println("Connected...");
      client.publish("/online/bedroom", "Online", true);
    }else{
      led_blink(4);
      Serial.println("failed with state...");
      Serial.print(client.state());
      delay(2000);
    }
  }

}

void loop() {
  unsigned long prevTime = 0;
  client.loop();
  while(!client.connected()){
    Serial.println("Connecting to MQTT Service..." + client.state());
    if(client.connect("Bedroom", mqtt_user, mqtt_pass, will_topic, will_qos, will_retain, will_message)){
      led_blink(2);
      client.subscribe("Door_Sensor_1");
      Serial.println("Connected...");
      client.publish("/online/bedroom", "Online", true);
    }else{
      led_blink(4);
      Serial.println("failed with state...");
      Serial.print(client.state());
      delay(2000);
    }
  }
  if(stateChanged){
    unsigned long currTime = millis();
    if(currTime - prevTime >= interval){
      prevTime = currTime;
      state = digitalRead(doorSwitch);
      if(state == 1){
        doorState = "Closed";
      }else{
        doorState = "Open";
      }
      stateChanged = false;
      Serial.println(state);
      client.publish("bedroom-door-status", doorState.c_str());
    }
  }
}