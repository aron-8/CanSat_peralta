#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP280.h>
#include <Adafruit_MPU6050.h>
#include <SPI.h>
#include <SD.h>
#include "lora.h"
//#include "MPU9250.h"
// MPU objektum létrehozása
#define WIRE1_SDA 26
#define WIRE1_SCL 27
arduino::MbedI2C Wire1(WIRE1_SDA, WIRE1_SCL);
// Adafruit_MPU6050 mpu; odl
Adafruit_MPU6050 mpu;
Adafruit_MPU6050 mpu1;
float ax;
float ay;
float az;
float gx;
float gy;
float gz;
float mpu_temp;
float ax1;
float ay1;
float az1;
float gx1;
float gy1;
float gz1;
float mpu_temp1;
// BMP280 objektum létrehozása
Adafruit_BMP280 bmp;

// SD kártya
const uint8_t SD_CS_PIN = 17;
File dataFile;

// gps ports
UART Serial2(8, 9, 0, 0);

unsigned int f = 500;            // ms mintavételi idő + ...
unsigned long previousMillis = 0; // lora üzenet küldéshez
unsigned long loop_time = 0;      // debug
uint32_t start = micros();        // febug

// gps adatok
int gpsTime;           // UTC idő
float latitude = 0.0;  // Szélességi fok (nem tizedes fokban)
float longitude = 0.0; // Hosszúsági fok (nem tizedes fokban)
float altitude = 0.0;  // Magasság (méterben)

String data;
String status; // modosítás saját tipusra
String gps;

const int keys[14][3] = { // minden loop ba számolnia kell!!? nem!!
    {0, 16000000, 1},
    {-5, 30, 100},
    {400, 1050, 100},
    {-320, 320, 100},
    {-320, 320, 100},
    {-320, 320, 100},
    {-10000, 10000, 1},
    {-10000, 10000, 1},
    {-10000, 10000, 1},
    {-5, 30, 100},
    {0, 240000, 1},
    {4580, 4851, 100000},
    {1600, 2250, 100000},
    {50, 3000, 10}};
String send_string_form[14];

void setup()
{

  Serial.begin(115200); // Debug célra (soros monitor)
  // while ((!Serial)){}

  // LoRa UART kommunikáció beállítása
  Serial1.begin(115200);
  delay(100);
  // attachInterrupt(digitalPinToInterrupt(1), ser, FALLING);

   Serial1.print("sys reset\r\n");
   wait_ok("WLR089");

  Serial1.println("radio rxstop");
  wait_ok();
  delay(100);
  Serial1.println("radio set sf sf9"); // alap 7!!
  wait_ok();
  Serial1.println("radio set bw 250"); // alap 125!!
  wait_ok();
  Serial1.println("radio set pwr 15"); // LoRa tejesítmény szint max 15
  wait_ok();
  Serial1.println("radio set freq 864625000"); // LoRa tejesítmény szint max 15
  wait_ok();
  //Serial1.println("radio set lbt 5 -80 10 1"); // LBT aktiv
  //wait_ok();
  Serial1.println("radio rx 0");
  wait_ok();
  // LED beállítása hibajelzéshez
  pinMode(LED_BUILTIN, OUTPUT);

  // SD kártya inicializálása
  if (!SD.begin(SD_CS_PIN))
  {
    //Serial.println("Hiba az SD kártya inicializálásakor");
    status += "h_SD";
  }
  else
  {
    //Serial.println("SD kártya inicializálva.");
    String name = "G";
    unsigned int copy = 1;
    while (SD.exists(name + ".txt")) // ne irja felül az előző logot
    {
      name = "G" + String(copy);
      copy += 1;
    }
    status += name;
    dataFile = SD.open(name + ".txt", FILE_WRITE);
  }

  // GPS inicializálása
  Serial2.begin(9600);
  if (!Serial2)
  {
    status += " no_GPS";
  }

  // BMP280 inicializálása
  if (!bmp.begin(0x76))
  {
    //Serial.println("Nem található BMP280!");
    status += " no_BMP";
  }
  else
  {
    //  // BMP280 beállítások
    bmp.setSampling(Adafruit_BMP280::MODE_NORMAL,
                    Adafruit_BMP280::SAMPLING_X2,   // Nyomás mintavételezés
                    Adafruit_BMP280::SAMPLING_X2,   // Hőmérséklet mintavételezés
                    Adafruit_BMP280::FILTER_X4,     // Szűrő
                    Adafruit_BMP280::STANDBY_MS_1); // Késleltetés
    //Serial.println("BMP280 inicializálva.");
  }

  // MPU6050 inicializálása

  Wire1.begin();
  delay(2000);
  //MPU9250Setting setting;
  // setting.accel_fs_sel = ACCEL_FS_SEL::A16G;
  // setting.gyro_fs_sel = GYRO_FS_SEL::G2000DPS;
  // setting.mag_output_bits = MAG_OUTPUT_BITS::M16BITS;
  // setting.fifo_sample_rate = FIFO_SAMPLE_RATE::SMPL_200HZ;
  // setting.gyro_fchoice = 0x03;
  // setting.gyro_dlpf_cfg = GYRO_DLPF_CFG::DLPF_41HZ;
  // setting.accel_fchoice = 0x01;
  // setting.accel_dlpf_cfg = ACCEL_DLPF_CFG::DLPF_45HZ;
  
  if (!mpu.begin(0x68, &Wire1)) // change to your own address
  {
    //Serial.println("Nem található MPU6050!");
    status += " no_MPU";
  }
  else
  {
    //Serial.println("MPU6050 inicializálva.");
    mpu.setAccelerometerRange(MPU6050_RANGE_16_G);
    mpu.setGyroRange(MPU6050_RANGE_250_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }
  if (!mpu1.begin(0x69, &Wire1)) // secund mpu
  {
    //Serial.println("Nem található MPU6050!");
    status += " no_MPU";
  }
  else
  {
    //Serial.println("MPU6050 inicializálva.");
    mpu1.setAccelerometerRange(MPU6050_RANGE_16_G);
    mpu1.setGyroRange(MPU6050_RANGE_250_DEG);
    mpu1.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  // hex formátum kódok hétrehozása
  for (int i = 0; i < 14; i++)
  {
    send_string_form[i] = hexNumFormat(keys[i][0], keys[i][1], keys[i][2]);
    //Serial.println(send_string_form[i]);
  }
}

void loop()
{

  // adatok a gps-ből
  while (Serial2.available() > 0)
  {
    String nmeaLine = Serial2.readStringUntil('\n'); // Egy teljes NMEA üzenet olvasása
    // //Serial.println(nmeaLine);
    gps = "";
    // csak a log ok hoz
    if (nmeaLine.startsWith("$GPGGA") and nmeaLine.indexOf("RMC") == -1) // 2. kell?
    {
      gps += nmeaLine;
      feldolgozGPGGA(nmeaLine, gpsTime, latitude, longitude, altitude);
    }
  }
  // BMP280 adatok beolvasása
  float temperature = bmp.readTemperature();
  float pressure = bmp.readPressure() / 100.0F; // hPa-ra alakítás
  // float al = bmp.readAltitude(1030.57);         // Tengerszint feletti magasság      VÁLTOZIK,  földön is lehet

  // MPU6050 adatok beolvasása
  
  sensors_event_t a, g, temp;
  if (mpu.getEvent(&a, &g, &temp))
  {
    ax = round(a.acceleration.x * 100) / 100;
    ay = round(a.acceleration.y * 100) / 100;
    az = round(a.acceleration.z * 100) / 100;
    gx = round(g.gyro.x);
    gy = round(g.gyro.y);
    gz = round(g.gyro.z);
    mpu_temp = round(temp.temperature * 100) / 100;
  }
  
  sensors_event_t a1, g1, temp1;
  if (mpu1.getEvent(&a1, &g1, &temp1))
  {
    ax1 = round(a1.acceleration.x * 100) / 100;
    ay1 = round(a1.acceleration.y * 100) / 100;
    az1 = round(a1.acceleration.z * 100) / 100;
    gx1 = round(g1.gyro.x);
    gy1 = round(g1.gyro.y);
    gz1 = round(g1.gyro.z);
    mpu_temp1 = round(temp1.temperature * 100) / 100;
  }
  // Adatok rgy str be
  String data = "&"; // kell? nem árt
  data += status;
  data += ",";
  data += millis();
  data += ",";
  data += temperature;
  data += ",";
  data += pressure;
  data += ",";
  data += ax;
  data += ",";
  data += ay;
  data += ",";
  data += az;
  data += ",";
  data += gx;
  data += ",";
  data += gy;
  data += ",";
  data += gz;
  data += ",";
  data += mpu_temp;
  data += ",";
  data += latitude;
  data += ",";
  data += longitude;
  data += ",";
  data += gpsTime;
  data += ",";
  data += altitude;
  data += ",";
  data += gps;
  data += ",";
  data += ax1;
  data += ",";
  data += ay1;
  data += ",";
  data += az1;
  data += ",";
  data += gx1;
  data += ",";
  data += gy1;
  data += ",";
  data += gz1;
  data += ",";
  data += mpu_temp1;

  // SD re írásű
  
  Serial.println(dataFile);
  if (dataFile)
  {
    dataFile.println(data);
    Serial.println("sd:");

    Serial.println(data);
    dataFile.flush();
  }
  else
  {
    //Serial.println("Hiba a fájl írásakor.");
  }

  // lora send all
  unsigned long currentMillis = millis();
  if (millis() - previousMillis >= f)
  {
    Serial1.println("radio rxstop");
    wait_ok();

    String all_send;

    all_send += toHexScaled((int)(millis() / 100), keys[0][0], keys[0][1], keys[0][2], send_string_form[0]);
    all_send += toHexScaled(temperature, keys[1][0], keys[1][1], keys[1][2], send_string_form[1]);
    all_send += toHexScaled(pressure, keys[2][0], keys[2][1], keys[2][2], send_string_form[2]);
    all_send += toHexScaled(ax, keys[3][0], keys[3][1], keys[3][2], send_string_form[3]);
    all_send += toHexScaled(ay, keys[4][0], keys[4][1], keys[4][2], send_string_form[4]);
    all_send += toHexScaled(az, keys[5][0], keys[5][1], keys[5][2], send_string_form[5]);
    all_send += toHexScaled(gx, keys[6][0], keys[6][1], keys[6][2], send_string_form[6]);
    all_send += toHexScaled(gy, keys[7][0], keys[7][1], keys[7][2], send_string_form[7]);
    all_send += toHexScaled(gz, keys[8][0], keys[8][1], keys[8][2], send_string_form[8]);
    all_send += toHexScaled(mpu_temp, keys[9][0], keys[9][1], keys[9][2], send_string_form[9]);
    all_send += toHexScaled(gpsTime, keys[10][0], keys[10][1], keys[10][2], send_string_form[10]);
    all_send += toHexScaled(latitude, keys[11][0], keys[11][1], keys[11][2], send_string_form[11]);
    all_send += toHexScaled(longitude, keys[12][0], keys[12][1], keys[12][2], send_string_form[12]);
    all_send += toHexScaled(altitude, keys[13][0], keys[13][1], keys[13][2], send_string_form[13]);


    previousMillis = currentMillis; // uj idő

    //Serial.println(data);
    //Serial.println(all_send.length());
    // //Serial.println(all_send);

    Serial1.print("radio tx "); // 73B  95096 µs 95ms
    
    

    Serial1.print(all_send);
    Serial1.println(" 1");
    wait_ok();
    start = micros();
    wait_ok("Total"); // ha nem sikeres cstorna váltás vagy ujra probálkozás!!!!
    //Serial.print("lora send time: ");
    // //Serial.print(all_send);
    //Serial.println(micros() - start);
    

    Serial1.println("radio rx 0");
wait_ok();
  }

  // delay(100); // Mintavételi sebesség beállítása radio tx ab 2

  String kommand = lora_hex_in();
  if (kommand.length() > 0)
  {
    //Serial.println(kommand);
    //Serial.println("radio rxstop");
    Serial1.println("radio rxstop");
    wait_ok();
    if (kommand.startsWith("1"))
    {
      delay(50);
      String comf = "radio tx ";
      comf += "ff";
      comf += " 1";
      //Serial.println(comf);
      Serial1.println(comf);
      wait_ok("Total");
      f = hexScaledtoint(kommand.substring(1), -1, 200000, 1);
      //Serial.print("uj kuldes ido :");
      //Serial.print(f);
    }
    if (kommand.startsWith("2"))
    {
      loracommand(kommand, 863000000, 870000000, 1000, "freq");
    }
    if (kommand.startsWith("3"))
    {
      loracommand(kommand, -4, 30, 1, "pwr");
    }
    if (kommand.startsWith("4"))
    {
      loracommand(kommand, 124, 600, 1, "bw");
    }
    if (kommand.startsWith("5"))
    {
      loracommand(kommand, 0, 20, 1, "sf", true);
    }
    if (kommand.startsWith("6"))
    {
      if (kommand[1] == '0')
      {
        //Serial.println("radio set lbt 5 -80 10 1");
        Serial1.println("radio set lbt 5 -80 10 0"); // LBT aktiv
        wait_ok();
      }
      else
      {
        //Serial.println("radio set lbt 5 -80 10 1");
        Serial1.println("radio set lbt 5 -80 10 0"); // LBT aktiv
        wait_ok();
      }
      delay(50);
      //Serial.println("radio tx ff 1");
      Serial1.println("radio tx ff 1");
      wait_ok("Total");
    }
    if (kommand.startsWith("7"))
    {
      if (kommand[1] == '1')
      {
        //Serial.println("sys reset");
        Serial1.println("sys reset"); // LBT aktiv
        wait_ok();
      }

      //Serial.println("radio tx ff 1");
      Serial1.println("radio tx ff 1");
      wait_ok("Total");
    }
    if (kommand.startsWith("8"))
    {
      long sl_t = hexScaledtoint(kommand.substring(1), 0, 1000000, 1);
      //Serial.println("sleep:");
      //Serial.println(sl_t);
      //Serial.println("radio tx ff 1");
      Serial1.println("radio tx ff 1");
      wait_ok("Total");
      sleep_ms(sl_t);
    }

    // //Serial.println("radio rx 0");
    // Serial1.println("radio rx 0");
  }

  if (millis() - loop_time > 400) // idő tullépés
  {

    //Serial.print("idő tullépés: ");
    //Serial.println(millis() - loop_time);
  }
  loop_time = millis();
}