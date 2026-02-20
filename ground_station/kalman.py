import numpy as np

def kalman_filter(data, Q=1e-5, R=1e-2):
    """
    Kálmán-szűrő implementáció egy dimenziós adatlistára.
    
    Args:
        data (list): Nyomásmérési adatok listája.
        Q (float): A folyamat zajának kovarianciája (szűrés érzékenysége).
        R (float): A mérési zaj kovarianciája.
    
    Returns:
        list: A szűrt adatok listája.
    """
    # Inicializálás
    n = len(data)
    x = np.zeros(n)  # Állapotbecslések
    P = np.zeros(n)  # Kovariancia becslések
    
    # Kezdeti állapotok
    x[0] = data[0]  # Első mért adat
    P[0] = 1.0      # Első kovariancia
    
    # Iterálás a mért adatokon
    for k in range(1, n):
        # 1. Predikció lépés
        x[k] = x[k-1]  # Előző állapotból predikált állapot
        P[k] = P[k-1] + Q  # Kovariancia frissítés
        
        # 2. Frissítés lépés
        K = P[k] / (P[k] + R)  # Kálmán-nyereség
        x[k] = x[k] + K * (data[k] - x[k])  # Állapot frissítése
        P[k] = (1 - K) * P[k]  # Kovariancia frissítése
    
    return x.tolist()


def kalman_filter_pressure_temperature_1d(pressure_data, temperature_data, Q, R, F, H):
    """
    Kálmán-szűrő 1D listákban tárolt nyomás- és hőmérséklet-adatokra.
    
    Args:
        pressure_data (list): Nyomásadatok listája.
        temperature_data (list): Hőmérséklet-adatok listája.
        Q (2x2 array): Folyamat zajának kovarianciája.
        R (2x2 array): Mérési zaj kovarianciája.
        F (2x2 array): Átmeneti mátrix.
        H (2x2 array): Mérési mátrix.
    
    Returns:
        tuple: (szűrt nyomás, szűrt hőmérséklet)
    """
    n = len(pressure_data)
    x = np.zeros((n, 2))  # Állapotvektor (nyomás, hőmérséklet)
    P = np.eye(2)         # Kovariancia mátrix

    # Kezdeti állapot
    x[0] = [pressure_data[0], temperature_data[0]]  # Kezdő nyomás és hőmérséklet

    for k in range(1, n):
        # 1. Predikció lépés
        x[k] = np.dot(F, x[k-1])  # Állapot predikció
        P = np.dot(np.dot(F, P), F.T) + Q  # Kovariancia predikció

        # 2. Mérési frissítés
        z = np.array([pressure_data[k], temperature_data[k]])  # Aktuális mérés
        S = np.dot(np.dot(H, P), H.T) + R  # Innováció kovarianciája
        K = np.dot(np.dot(P, H.T), np.linalg.inv(S))  # Kálmán-nyereség
        x[k] = x[k] + np.dot(K, (z - np.dot(H, x[k])))  # Állapot frissítése
        P = np.dot((np.eye(2) - np.dot(K, H)), P)      # Kovariancia frissítése
    
    # Szűrt adatokat külön listákba bontjuk
    filtered_pressure = x[:, 0].tolist()
    filtered_temperature = x[:, 1].tolist()

    return filtered_pressure, filtered_temperature

