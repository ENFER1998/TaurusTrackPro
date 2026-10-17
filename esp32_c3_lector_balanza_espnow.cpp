/**
 * ============================================================================
 * TAURUS TRACK PRO - NODO 2: LECTOR DE BALANZA + ESP-NOW DE ALTA FIABILIDAD
 * ============================================================================
 * Placa objetivo: ESP32-C3 Super Mini
 *
 * Características principales:
 * 1. Respuesta inmediata de ACK en ráfaga (x2) ante consulta del Lector RFID
 *    para superar cualquier colisión RF con el Bluetooth del Nodo 1.
 * 2. Envío de Peso Estable en ráfaga (x3 con control de secuencia) hacia el
 *    Nodo 1 para garantizar entrega 100% confiable en manga/brete.
 * 3. Lectura serie RS232/UART1 (GPIO 4/5) y USB totalmente NO BLOQUEANTE con
 *    estabilización inteligente para cabezales de balanza continuos o por disparo.
 * 4. Funciona tanto en modo combinado (asociado a la caravana recibida del Nodo 1)
 *    como en pesaje directo (envía el peso al Nodo 1 aunque no se haya leído RFID).
 *
 * Configuración en Arduino IDE:
 * - Board: "ESP32C3 Dev Module" o "LOLIN C3 Mini"
 * - USB CDC On Boot: "Enabled"
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>
#include <math.h>

// ==================== PINES ESP32-C3 SUPER MINI ====================
constexpr int PIN_LED_STATUS  = 8;  // LED azul integrado (activo en LOW)
constexpr int PIN_BTN_TEST    = 9;  // Botón BOOT integrado para simular un pesaje
constexpr int PIN_BALANZA_RX  = 4;  // RX para cabezal de balanza RS232/UART
constexpr int PIN_BALANZA_TX  = 5;  // TX para cabezal de balanza RS232/UART

// ==================== CONFIGURACIÓN ESP-NOW ====================
constexpr uint8_t ESPNOW_WIFI_CHANNEL = 1;
constexpr unsigned long INTERVALO_HEARTBEAT_MS = 1800;

uint8_t macLectorRfidPeer[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

enum TipoMensaje : uint8_t {
  MSG_RFID_DETECTADO     = 1,
  MSG_PESO_ESTABLE       = 2,
  MSG_ACK_BALANZA_ONLINE = 3,
  MSG_HEARTBEAT_BALANZA  = 4
};

struct __attribute__((packed)) PaqueteGanado {
  uint8_t tipoMensaje;
  char rfid[24];
  float pesoKg;
  uint32_t secuencia;
};

// ==================== ESTADO DEL SISTEMA ====================
volatile bool nuevaCaravanaEnBrete = false;
PaqueteGanado ultimoPaqueteRfid;
char caravanaActual[24] = "";
uint32_t ultimaSecuenciaRfidRecibida = 0;
uint32_t secuenciaPesaje = 0;

unsigned long ultimoTiempoBoton = 0;
unsigned long ultimoTiempoHeartbeat = 0;
constexpr unsigned long DEBOUNCE_MS = 350;

// Buffers no bloqueantes y filtro de estabilización para cabezal físico RS232
char bufferUsb[64];
size_t idxUsb = 0;
char bufferBalanza[64];
size_t idxBalanza = 0;

float lecturasRecientes[3] = {0.0f, 0.0f, 0.0f};
int conteoLecturasEstables = 0;
unsigned long tiempoUltimaTramaBalanza = 0;
bool esperandoConfirmarDisparoUnico = false;
float ultimoPesoDisparo = 0.0f;
unsigned long tiempoUltimoPesoEnviadoSerie = 0;

// ==================== CALLBACKS ESP-NOW ====================
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
void alEnviarEspNow(const wifi_tx_info_t* info, esp_now_send_status_t status) {
  (void)info;
  (void)status;
}
#else
void alEnviarEspNow(const uint8_t* mac_addr, esp_now_send_status_t status) {
  (void)mac_addr;
  (void)status;
}
#endif

#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
void alRecibirEspNow(const esp_now_recv_info_t* info, const uint8_t* datos, int longitud) {
  (void)info;
#else
void alRecibirEspNow(const uint8_t* mac, const uint8_t* datos, int longitud) {
  (void)mac;
#endif
  if (longitud != sizeof(PaqueteGanado)) {
    return;
  }

  PaqueteGanado paqueteEntrante;
  memcpy(&paqueteEntrante, datos, sizeof(PaqueteGanado));

  if (paqueteEntrante.tipoMensaje == MSG_RFID_DETECTADO) {
    memcpy((void*)&ultimoPaqueteRfid, &paqueteEntrante, sizeof(PaqueteGanado));
    nuevaCaravanaEnBrete = true;
  }
}

// ==================== FUNCIONES AUXILIARES ====================
void parpadearLed(int repeticiones, int duracionMs) {
  for (int i = 0; i < repeticiones; i++) {
    digitalWrite(PIN_LED_STATUS, LOW);
    delay(duracionMs);
    digitalWrite(PIN_LED_STATUS, HIGH);
    delay(duracionMs);
  }
}

void confirmarBalanzaOnline(const char* rfidRecibido, uint32_t secuencia) {
  PaqueteGanado paqueteAck = {};
  paqueteAck.tipoMensaje = MSG_ACK_BALANZA_ONLINE;
  strncpy(paqueteAck.rfid, rfidRecibido, sizeof(paqueteAck.rfid) - 1);
  paqueteAck.pesoKg = 0.0f;
  paqueteAck.secuencia = secuencia;

  // Doble envío separado por 12 ms para asegurar recepción frente a coexistencia BLE en Nodo 1
  esp_now_send(macLectorRfidPeer, (uint8_t*)&paqueteAck, sizeof(paqueteAck));
  delay(12);
  esp_now_send(macLectorRfidPeer, (uint8_t*)&paqueteAck, sizeof(paqueteAck));
}

void enviarHeartbeatBalanza() {
  PaqueteGanado paqueteHb = {};
  paqueteHb.tipoMensaje = MSG_HEARTBEAT_BALANZA;
  paqueteHb.pesoKg = 0.0f;
  paqueteHb.secuencia = secuenciaPesaje;

  esp_now_send(macLectorRfidPeer, (uint8_t*)&paqueteHb, sizeof(paqueteHb));
}

float extraerNumeroDeTrama(const String& trama) {
  String numeroLimpio = "";
  bool puntoVisto = false;

  for (size_t i = 0; i < trama.length(); i++) {
    char c = trama[i];
    if (isdigit((unsigned char)c)) {
      numeroLimpio += c;
    } else if ((c == '.' || c == ',') && !puntoVisto && numeroLimpio.length() > 0) {
      numeroLimpio += '.';
      puntoVisto = true;
    }
  }

  return numeroLimpio.toFloat();
}

void enviarPesoAlRfid(float pesoKg) {
  if (pesoKg <= 0.0f) {
    Serial.println("[AVISO] El peso debe ser mayor a 0 kg.");
    return;
  }

  secuenciaPesaje++;
  PaqueteGanado paquetePeso = {};
  paquetePeso.tipoMensaje = MSG_PESO_ESTABLE;
  strncpy(paquetePeso.rfid, caravanaActual, sizeof(paquetePeso.rfid) - 1);
  paquetePeso.pesoKg = pesoKg;
  paquetePeso.secuencia = secuenciaPesaje;

  Serial.println("-----------------------------------------");
  Serial.print("[BALANZA] Enviando peso por ESP-NOW: ");
  Serial.print(pesoKg, 2);
  if (strlen(caravanaActual) > 0) {
    Serial.print(" kg -> Caravana: ");
    Serial.println(caravanaActual);
  } else {
    Serial.println(" kg (Modo Solo Peso)");
  }

  // Envío redundante x3 con el mismo número de secuencia (Nodo 1 filtra duplicados)
  for (int i = 0; i < 3; i++) {
    esp_now_send(macLectorRfidPeer, (uint8_t*)&paquetePeso, sizeof(paquetePeso));
    if (i < 2) delay(15);
  }

  caravanaActual[0] = '\0';
  conteoLecturasEstables = 0;
  esperandoConfirmarDisparoUnico = false;
  parpadearLed(2, 80);
}

void procesarTramaCabezalBalanza(const String& tramaRaw) {
  String upper = tramaRaw;
  upper.toUpperCase();

  // Ignorar tramas explícitamente marcadas como inestables por el cabezal (US = Unstable, MOTION)
  if (upper.indexOf("US,") >= 0 || upper.indexOf("MOTION") >= 0) {
    conteoLecturasEstables = 0;
    esperandoConfirmarDisparoUnico = false;
    return;
  }

  float peso = extraerNumeroDeTrama(tramaRaw);
  unsigned long ahora = millis();

  // Si la plataforma se vacía (< 5 kg), resetear bloqueo para el siguiente animal
  if (peso < 5.0f) {
    conteoLecturasEstables = 0;
    esperandoConfirmarDisparoUnico = false;
    return;
  }

  // Cooldown para no reenviar en bucle continuo al mismo animal parado sobre la plataforma
  if (strlen(caravanaActual) == 0 && (ahora - tiempoUltimoPesoEnviadoSerie < 4000)) {
    return;
  }

  // Si el cabezal envía la etiqueta explícita de estabilidad "ST," (ej. Toledo/Ohaus/Tru-Test)
  if (upper.indexOf("ST,") >= 0) {
    tiempoUltimoPesoEnviadoSerie = ahora;
    enviarPesoAlRfid(peso);
    return;
  }

  // Si es una ráfaga continua del cabezal (tramas cada < 300 ms), exigir 3 lecturas iguales (±1.0 kg)
  if (ahora - tiempoUltimaTramaBalanza < 300) {
    esperandoConfirmarDisparoUnico = false;
    if (conteoLecturasEstables == 0) {
      lecturasRecientes[0] = peso;
      conteoLecturasEstables = 1;
    } else {
      float ref = lecturasRecientes[conteoLecturasEstables - 1];
      if (fabsf(peso - ref) <= 1.0f) {
        lecturasRecientes[conteoLecturasEstables] = peso;
        conteoLecturasEstables++;
        if (conteoLecturasEstables >= 3) {
          float promedio = (lecturasRecientes[0] + lecturasRecientes[1] + lecturasRecientes[2]) / 3.0f;
          tiempoUltimoPesoEnviadoSerie = ahora;
          enviarPesoAlRfid(promedio);
        }
      } else {
        lecturasRecientes[0] = peso;
        conteoLecturasEstables = 1;
      }
    }
  } else {
    // Primera trama aislada: puede ser un cabezal de disparo único (botón PRINT) o el inicio de un flujo
    lecturasRecientes[0] = peso;
    conteoLecturasEstables = 1;
    ultimoPesoDisparo = peso;
    esperandoConfirmarDisparoUnico = true;
  }

  tiempoUltimaTramaBalanza = ahora;
}

void inicializarEspNow() {
  WiFi.mode(WIFI_STA);
  esp_wifi_set_ps(WIFI_PS_MIN_MODEM);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  esp_wifi_set_channel(ESPNOW_WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

  Serial.print("[WIFI] MAC de esta Balanza: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("[ERROR] No se pudo inicializar ESP-NOW.");
    return;
  }

  esp_now_register_send_cb(alEnviarEspNow);
  esp_now_register_recv_cb(alRecibirEspNow);

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, macLectorRfidPeer, 6);
  peerInfo.channel = ESPNOW_WIFI_CHANNEL;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("[ERROR] Falló el registro del peer RFID.");
  } else {
    Serial.println("[ESP-NOW] Listo en canal 1.");
  }
}

// ==================== SETUP & LOOP ====================
void setup() {
  pinMode(PIN_LED_STATUS, OUTPUT);
  digitalWrite(PIN_LED_STATUS, HIGH);
  pinMode(PIN_BTN_TEST, INPUT_PULLUP);

  Serial.begin(115200);
  Serial1.begin(9600, SERIAL_8N1, PIN_BALANZA_RX, PIN_BALANZA_TX);

  randomSeed(micros());
  delay(800);
  Serial.println("\n=== INICIANDO NODO 2: BALANZA TAURUS TRACK PRO ===");

  inicializarEspNow();
  parpadearLed(3, 100);
}

void loop() {
  unsigned long ahora = millis();

  // 1. RECEPCIÓN DE CARAVANA DESDE EL NODO 1 (LECTOR RFID)
  if (nuevaCaravanaEnBrete) {
    PaqueteGanado paqueteLocal;
    noInterrupts();
    memcpy(&paqueteLocal, (const void*)&ultimoPaqueteRfid, sizeof(PaqueteGanado));
    nuevaCaravanaEnBrete = false;
    interrupts();

    // Siempre enviar ACK inmediato por si el primer ACK colisionó
    confirmarBalanzaOnline(paqueteLocal.rfid, paqueteLocal.secuencia);

    if (paqueteLocal.secuencia != ultimaSecuenciaRfidRecibida || strcmp(caravanaActual, paqueteLocal.rfid) != 0) {
      ultimaSecuenciaRfidRecibida = paqueteLocal.secuencia;
      strncpy(caravanaActual, paqueteLocal.rfid, sizeof(caravanaActual) - 1);
      caravanaActual[sizeof(caravanaActual) - 1] = '\0';
      conteoLecturasEstables = 0;
      esperandoConfirmarDisparoUnico = false;

      Serial.println("=========================================");
      Serial.print("[ESP-NOW] Caravana recibida (ACK enviado): ");
      Serial.println(caravanaActual);
      Serial.println("[BALANZA] Esperando estabilización de peso...");
      Serial.println("=========================================");
    }
  }

  // 2. HEARTBEAT PERIÓDICO PARA QUE EL NODO 1 SEPA QUE LA BALANZA ESTÁ ENCENDIDA
  if (ahora - ultimoTiempoHeartbeat >= INTERVALO_HEARTBEAT_MS) {
    ultimoTiempoHeartbeat = ahora;
    enviarHeartbeatBalanza();
  }

  // 3. PRUEBA CON BOTÓN BOOT (GPIO 9): Simula un pesaje inmediato
  if (digitalRead(PIN_BTN_TEST) == LOW) {
    if (ahora - ultimoTiempoBoton > DEBOUNCE_MS) {
      ultimoTiempoBoton = ahora;
      float pesoSimulado = 380.0f + (random(0, 281) * 0.5f);
      enviarPesoAlRfid(pesoSimulado);
    }
  }

  // 4. PRUEBA POR MONITOR SERIE USB (No bloqueante, envío inmediato)
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (idxUsb > 0) {
        bufferUsb[idxUsb] = '\0';
        idxUsb = 0;
        float pesoManual = extraerNumeroDeTrama(String(bufferUsb));
        enviarPesoAlRfid(pesoManual);
      }
    } else if (idxUsb < sizeof(bufferUsb) - 1) {
      bufferUsb[idxUsb++] = c;
    }
  }

  // 5. LECTURA DESDE CABEZAL DE BALANZA FÍSICO POR UART1 (GPIO 4/5, No bloqueante)
  while (Serial1.available() > 0) {
    char c = (char)Serial1.read();
    if (c == '\n' || c == '\r' || c == 0x03) {
      if (idxBalanza > 0) {
        bufferBalanza[idxBalanza] = '\0';
        idxBalanza = 0;
        procesarTramaCabezalBalanza(String(bufferBalanza));
      }
    } else if (c >= 32 && c <= 126 && idxBalanza < sizeof(bufferBalanza) - 1) {
      bufferBalanza[idxBalanza++] = c;
    }
  }

  // Si el cabezal físico envió un único disparo (modo botón PRINT) y no llegaron más tramas en 350 ms
  if (esperandoConfirmarDisparoUnico && (ahora - tiempoUltimaTramaBalanza >= 350)) {
    esperandoConfirmarDisparoUnico = false;
    if (ultimoPesoDisparo >= 5.0f) {
      tiempoUltimoPesoEnviadoSerie = ahora;
      enviarPesoAlRfid(ultimoPesoDisparo);
    }
  }

  // LED azul fijo cuando hay una caravana en el brete esperando su peso
  digitalWrite(PIN_LED_STATUS, (strlen(caravanaActual) > 0) ? LOW : HIGH);
}