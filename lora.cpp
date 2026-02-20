#include <Arduino.h>
#include "lora.h"

void wait_ok(String mit)
{
  unsigned long time_end = millis() + 1000;
  while (time_end > millis())
  {
    if (Serial1.available())
    {
      String response = Serial1.readStringUntil('\n'); // Válasz olvasása sor végéig
                                                       // Serial.println(response);
      if (response.startsWith(mit))
      {
        Serial.println(response);
        break;
      }
      else
      {
        Serial.println(response);
      }
    }
  }
}

String lora_hex_in()
{
  String response;
  while (Serial1.available() > 0)
  {
    int res = (Serial1.read()); // Válasz olvasása sor végéig
    response += (char)res;
  }
  // Serial.println(response);
  int spaceIndex = response.indexOf(" "); // Szóköz indexének keresése
  // Serial.println(spaceIndex);
  if (spaceIndex == -1)
  {
    // Ha nincs szóköz, üres stringet adunk vissza
    return response;
  }
  response = response.substring(spaceIndex + 1);
  response.trim();
  return response; // A szóköz utáni rész visszaadása
}

int hexScaledtoint(String hex, int minVal, int maxVal, int resolution)
{

  int valZ = (int)strtol(hex.c_str(), NULL, 16);
  int val = valZ * resolution;
  val = val + (long)minVal;
  if (val >= minVal and val <= maxVal)
  {
    return val;
  }
  else
  {
    return 0;
  }
}
String hexNumFormat(int minVal, int maxVal, int resolution)
{

  unsigned int bit_number = (log2((maxVal - minVal + 1) * (resolution)) + 1);
  unsigned int hex_number = (bit_number / 4 + 1);

  String hex_format_num = "%0";
  hex_format_num += String(hex_number);
  hex_format_num += "x";

  return hex_format_num;
}

String toHexScaled(float value, int minVal, int maxVal, int resolution, String hex_format_num)
{
  char buffer[20];
  if (value >= minVal and value <= maxVal)
  {

    unsigned long val_Z = round((value - minVal) * (resolution));

    sprintf(buffer, hex_format_num.c_str(), val_Z);
  }
  else
  {
    sprintf(buffer, hex_format_num.c_str(), 0);
  }
  return buffer;
}

// NMEA üzenet mezőire bontása
void splitNMEA(String nmea, String *mezok, int maxMezok)
{
  int idx = 0;
  for (int i = 0; i < maxMezok; i++)
  {
    int delimiterIdx = nmea.indexOf(',', idx);
    if (delimiterIdx == -1)
    {
      mezok[i] = nmea.substring(idx);
      break;
    }
    mezok[i] = nmea.substring(idx, delimiterIdx);
    idx = delimiterIdx + 1;
  }
}

// $GPGGA üzenet feldolgozása
void feldolgozGPGGA(String nmea, int &gpsTime, float &latitude, float &longitude, float &altitude)
{
  String mezok[15];
  splitNMEA(nmea, mezok, 15);

  // Adatok tárolása változókban
  gpsTime = mezok[1].toInt();
  latitude = mezok[2].toFloat();
  ;
  longitude = mezok[4].toFloat();
  altitude = mezok[9].toFloat();
}

String stringToLoRaSend(String input)
{ // str data to hex  + " 1"- egyszer küldje
  String hexOutput = "radio tx ";
  for (unsigned int i = 0; i < input.length(); i++)
  {
    char c = input.charAt(i);
    if (c < 16)
    {                   //?
      hexOutput += "0"; // Ensure leading zero for single-digit hex values
    }
    hexOutput += String(c, HEX); // Convert character to hex
  }

  return hexOutput + " 1";
}

void loracommand(String kommand, int minval, int maxVal, int resolution, String mit, bool sf)
{
    int new_dat = hexScaledtoint(kommand.substring(1), minval, maxVal, resolution);
    delay(50);
    String comf = "radio tx ";
    comf += "ff";
    comf += " 1";
    Serial.println(comf);
    Serial1.println(comf);
    wait_ok("Total");

    String kom = "radio set ";
    
    kom += mit;
    kom +=" ";
    if (sf==true){kom +="sf";}
    kom += String(new_dat);

    Serial.println(kom);
    Serial1.println(kom);
    wait_ok();
}
    
void loraget(String mit){
    String kom = "radio get ";
    kom += mit;

    Serial.println(kom);
    Serial1.println(kom);
    String response = Serial1.readStringUntil('\n');;
    response.trim();
    delay(1000);
    Serial.println(stringToLoRaSend(response));
    Serial1.println(stringToLoRaSend(response));
    wait_ok("Total");


}