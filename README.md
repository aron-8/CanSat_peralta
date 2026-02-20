# CanSat_peralta
ESA CanSat Competition 2025 - Peralta Team. Miniature satellite with RP2040 firmware, LoRa telemetry, and Python/Kivy ground station.
CanSat - Peralta Team (ESA Competition 2025)



Ez a projekt a Peralta Team fejlesztése az Európai Űrügynökség (ESA) CanSat versenyére. A projekt célja egy üdítősdoboz méretű műhold tervezése és építése, amely képes valós idejű telemetriai adatok gyűjtésére és komplex aerodinamikai elemzések elvégzésére.

Küldetések

1. Elsődleges küldetés

Hőmérséklet és nyomás mérése: Folyamatos adatgyűjtés az ereszkedés során.

Telemetria: Valós idejű adattovábbítás LoRa protokollon keresztül a földi állomásra.

Adatnaplózás: Az összes mért paraméter redundáns mentése SD kártyára.

2. Másodlagos küldetés: Aerodinamikai elemzés

Alaki tényező ($c$) számítása: Az ejtőernyő légellenállási együtthatójának meghatározása a süllyedési sebesség és a légsűrűség függvényében.

Kálmán-szűrő alkalmazása: A szenzorzaj (különösen a barometrikus magasság) kiszűrése a pontosabb süllyedési profil meghatározásához.

Stabilitásmérés: A műhold süllyedés közbeni oszcillációjának elemzése 9-tengelyes IMU segítségével.

 Hardver Architektúra

Központi egység: Raspberry Pi Pico (RP2040)

Szenzorok:

BMP280: Precíziós légnyomás- és hőmérsékletszenzor.

MPU9250 (x2): Gyorsulásmérő, giroszkóp és magnetométer (redundáns kiépítés).

Neo-7 GPS: Helymeghatározás és UTC időszinkron.

Kommunikáció: WLR089 LoRa modul (868 MHz), ~3 km hatótávolság.

Energiaellátás: 1200mAh Li-Po akkumulátor, TP4056 töltésvezérlővel.

Váz: Egyedi tervezésű (OnShape), 3D nyomtatott PLA szerkezet, belső sínrendszerrel a PCB rögzítéséhez.

Szoftveres Megoldások

On-Board Data Handling (OBDH) - C++ / Arduino

A műhold szoftvere egy optimalizált hurokban fut, amely kezeli az I2C (szenzorok), UART (LoRa, GPS) és SPI (SD kártya) kommunikációt.

Adattömörítés: A sávszélesség hatékony kihasználása érdekében a telemetriai adatokat egyedi hexadecimális kódolással tömörítjük küldés előtt.

Hibakezelés: Automatikus modul-újraindítás és hiba-naplózás a misszió folytonossága érdekében.

Ground Station - Python / Kivy

Egy egyedi fejlesztésű GUI alkalmazás biztosítja a kapcsolatot a műholddal.

Interaktív vezérlés: Távoli parancsküldés (pl. Spreading Factor állítás, mintavételezési gyakoriság módosítása).

Élő vizualizáció: Valós idejű grafikonok és GPS-alapú helymeghatározás (Google Maps integráció).

Többszálú végrehajtás: A soros port olvasása és a UI frissítése külön szálon fut a folyamatos működés érdekében.

Data Analysis - Python / Pandas / Matplotlib

A repülés utáni elemzést egy Python script végzi, amely az SD kártyáról beolvasott nyers adatokat dolgozza fel.

Kálmán-szűrő: 1D és 2D szűrő a magassági adatok simítására.

Fizikai modellezés: Magasság számítása barometrikus formulával és süllyedési görbe illesztése.

Mentőrendszer (Recovery)

Ejtőernyő: 60 cm átmérőjű, hatszögletű ripstop szövet, 6 cm-es stabilizáló lyukkal.

Zsinórok: 1.18 mm-es Dyneema szálak (200 kg szakítószilárdság).

Tesztelés: Sikeres 20G-s gyorsulási teszt és videóalapú sebességelemzés (Tracker software).

A csapat

Kovács Áron: Szoftverfejlesztés (OBDH, GUI), elektronika, 3D tervezés.

Csányi Ákos: Mentőrendszer tervezése, logó és design.

Fazekas-Szűcs Barnabás: Dokumentáció, média tartalom.

Költő Bence: 3D modellezés, animáció.

Siklósi Péter: Adatelemzés, matematikai optimalizáció.
