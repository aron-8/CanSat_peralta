import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from kalman import kalman_filter

def calculate_altitude(pressure_hpa, sea_level_hpa=1013.25):
    """
    Kiszámítja a magasságot a barometrikus formula alapján.
    """
    return 44330 * (1.0 - (pressure_hpa / sea_level_hpa) ** 0.1903)

def load_and_parse_sd_data(filepath):
    """
    Beolvassa az SD kártya log fájlját, és kinyeri belőle az alapvető telemetriát.
    A main.cpp struktúrájára épít:
    &status, millis, temp, pressure, ax, ay, az, gx, gy, gz, mpu_temp, lat, lon, gpsTime, alt, gpsStr...
    """
    times = []
    pressures = []
    temperatures = []
    
    try:
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                # Csak az érvényes, adatsorokat tartalmazó sorokat dolgozzuk fel
                if not line.startswith('&'):
                    continue
                
                parts = line.split(',')
                try:
                    # Adatok kinyerése és konvertálása
                    t_ms = float(parts[1])
                    temp = float(parts[2])
                    press = float(parts[3])
                    
                    # Hibás (pl. 0 vagy extrém) szenzoradatok kiszűrése
                    if press > 800 and press < 1100: 
                        times.append(t_ms / 1000.0) # Szekundumra váltás
                        temperatures.append(temp)
                        pressures.append(press)
                except (ValueError, IndexError):
                    # Ha egy sor hibás (pl. megszakadt mentés), kihagyjuk
                    pass
                    
    except FileNotFoundError:
        print(f"Hiba: A '{filepath}' fájl nem található!")
        return None
        
    # DataFrame-be rakjuk a könnyebb kezelésért
    df = pd.DataFrame({
        'Time_s': times,
        'Temperature_C': temperatures,
        'Pressure_hPa': pressures
    })
    
    # Idő normalizálása (0-tól induljon a kilövéskor)
    if not df.empty:
        df['Time_s'] = df['Time_s'] - df['Time_s'].iloc[0]
        
    return df

def main():
    # 1. Adatok betöltése (Cseréld ki a teszt fájlod nevére, pl: 'G1.txt')
    # Ha nincs még fájlod, teszteléshez generálhatsz bele egy dummy datasetet.
    data_file = 'G1.txt' 
    print(f"Adatok beolvasása a(z) {data_file} fájlból...")
    df = load_and_parse_sd_data(data_file)
    
    if df is None or df.empty:
        print("Nem sikerült adatot kinyerni. Ellenőrizd a fájl elérési útját!")
        return

    # 2. Nyers Magasság Kiszámítása
    # A kiindulási nyomást vehetjük az első pár mérés átlagából (földszint)
    ground_pressure = df['Pressure_hPa'].iloc[:10].mean()
    df['Raw_Altitude_m'] = calculate_altitude(df['Pressure_hPa'], sea_level_hpa=ground_pressure)

    # 3. Kálmán-szűrő alkalmazása
    # Q: Folyamat zaj (kisebb érték jobban bízik a modellben, lassabban követ)
    # R: Mérési zaj (nagyobb érték jobban simítja a zajos szenzoradatot)
    print("Kálmán-szűrő alkalmazása az adatokra...")
    filtered_alt = kalman_filter(df['Raw_Altitude_m'].tolist(), Q=1e-4, R=5e-1)
    df['Kalman_Altitude_m'] = filtered_alt

    # Opcionális: Szűrjük meg a nyomást is magát a demonstráció kedvéért
    filtered_press = kalman_filter(df['Pressure_hPa'].tolist(), Q=1e-5, R=1e-1)
    df['Kalman_Pressure_hPa'] = filtered_press

    # 4. Vizualizáció
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # Felső grafikon: Magasság (Nyers vs Szűrt)
    ax1.plot(df['Time_s'], df['Raw_Altitude_m'], label='Nyers Magasság (BMP280)', color='red', alpha=0.5, linewidth=1)
    ax1.plot(df['Time_s'], df['Kalman_Altitude_m'], label='Kálmán-szűrt Magasság', color='blue', linewidth=2)
    ax1.set_ylabel('Magasság (m)', fontsize=12)
    ax1.set_title('CanSat Repülési Profil (Magasság)', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right')

    # Alsó grafikon: Légnyomás
    ax2.plot(df['Time_s'], df['Pressure_hPa'], label='Nyers Légnyomás', color='orange', alpha=0.5, linewidth=1)
    ax2.plot(df['Time_s'], df['Kalman_Pressure_hPa'], label='Kálmán-szűrt Légnyomás', color='green', linewidth=2)
    ax2.set_xlabel('Idő (s)', fontsize=12)
    ax2.set_ylabel('Nyomás (hPa)', fontsize=12)
    ax2.set_title('Mért Légnyomás', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right')

    plt.tight_layout()
    
    # Kép mentése
    plt.savefig('cansat_kalman_filter_results.png', dpi=300)
    print("Kész! A grafikon elmentve 'cansat_kalman_filter_results.png' néven.")
    plt.show()

if __name__ == "__main__":
    main()