import serial
import time
import threading
import webbrowser
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock, mainthread
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

# Ha a kalman.py ugyanabban a mappában van:
# from kalman import kalman_filter, kalman_filter_pressure_temperature_1d

class UARTApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)

        # UI Téma beállítása (Sötétzöld)
        Window.clearcolor = (0, 0.1, 0, 1)
          
        # Soros port inicializálása
        self.com_port = "COM22" # TODO: Ezt érdemes lehet egy UI mezőből beolvasni később
        try:
            self.serial_port = serial.Serial(self.com_port, baudrate=115200, timeout=1)
            print(f"Sikeres csatlakozás: {self.com_port}")
        except Exception as e:
            print(f"Hiba a soros port megnyitásakor ({self.com_port}): {e}")
            self.serial_port = None
        
        self.progress = False
        self.package_rate = 0.6
        self.countdown_time = self.package_rate
        self.snr = True
        self.pktrssi = True
        self.flag = 0

        # Adatstruktúrák és konstansok (Globális változók helyett osztályszintű attribútumok)
        self.key = [0, 7, 11, 16, 21, 26, 31, 35, 39, 43, 47, 52, 59, 66, 70]
        self.keydata = [
            [0, 16000000, 1], [-5, 30, 0.01], [400, 1050, 0.01],
            [-320, 320, 0.01], [-320, 320, 0.01], [-320, 320, 0.01],
            [-10000, 10000, 1], [-10000, 10000, 1], [-10000, 10000, 1],
            [-5, 30, 0.01], [0, 240000, 1], [4580, 4851, 0.00001],
            [1600, 2250, 0.00001], [50, 3000, 0.1]
        ]
        
        self.data_name_list = [
            "time", "temperature", "pressure", "a.x", "a.y", "a.z", 
            "g.x", "g.y", "g.z", "mpu_temp", "gps Time", "gps lat", 
            "gps lon", "gps alt", "alt"
        ]
        
        # 21 üres lista inicializálása az adatoknak
        self.all_data = [[] for _ in range(21)]
        
        self.kommands_1 = ["radio rx 0", "radio rxstop", "radio get freq", "radio get pwr", 
                           "radio get sf", "radio get bw", "sys reset", "radio set pwr ", 
                           "radio set sf sf", "radio set bw ", "radio set freq "]
        self.button_names = ["sending speed(ms)", "set freq (kHz)", "set pwr", "set bw", 
                             "set sf", "set LBT (0/1)", "reset(0/1)", "sleep (ms)", 
                             "clear", "gps in map"]
        self.comf_b1 = ["0", "radio set freq ", "radio set pwr ", "radio set bw ", 
                        "radio set sf sf", "set LBT (0/1)", "reset(0/1)", "sleep (ms)", 
                        "diagrams", "gps in map"]
        self.keyCansat = [[-1, 1, 5], [863000, 1, 5], [-4, 1, 3], [124, 1, 3], 
                          [0, 1, 1], [0, 1, 1], [0, 1, 1], [0, 1, 5]]

        self._build_ui()
        self._init_matplotlib()

        # Alapértelmezett rádió beállítások kiküldése inicializáláskor
        if self.serial_port and self.serial_port.is_open:
            self._setup_radio_defaults()

        # Időzítők indítása
        Clock.schedule_interval(self.read_from_uart, 0.1)
        Clock.schedule_interval(self.update_countdown, 0.1)
        Clock.schedule_interval(self.update_diagram, 0.5) # Kicsit ritkábban frissítjük a rajzot, hogy ne akadjon a Kivy

    def _build_ui(self):
        """Grafikus felület elemeinek felépítése"""
        # Bal oldali panel (Parancsok)
        self.left_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        for i in range(0, 7):
            btn = Button(text=self.kommands_1[i], font_size=14,
                         background_color=(0, 0.08*i, 0.3/(1+i), 1), color=(1, 1, 1, 1),
                         on_press=lambda x, cmd=self.kommands_1[i]: self.send_command(cmd))
            self.left_layout.add_widget(btn)
            
        for i in range(7, 11):
            btn = Button(text=self.kommands_1[i], font_size=14,
                         background_color=(0, 0.08*i, 0, 1), color=(1, 1, 1, 1),
                         on_press=lambda x, cmd=self.kommands_1[i]: self.send_command_part(cmd))
            self.left_layout.add_widget(btn)

        self.toggle_1 = Button(text="snr : ON", font_size=14, background_color=(0, 0.5, 0, 1),
                               color=(1, 1, 1, 1), on_press=self.toggle_button_1)
        self.left_layout.add_widget(self.toggle_1)

        self.toggle_3 = Button(text="pktrssi : ON", font_size=14, background_color=(0, 0.5, 0, 1),
                               color=(1, 1, 1, 1), on_press=self.toggle_button_3)
        self.left_layout.add_widget(self.toggle_3)

        # Középső panel (Naplózás és input)
        self.center_layout = BoxLayout(orientation='vertical', size_hint=(0.6, 1))
        self.countdown_label = Label(text=f"New data: {self.countdown_time:.1f}",
                                     size_hint=(1, 0.05), font_size=20, color=(0, 1, 0, 1))
        self.received_label = Label(text="Received Data, miss: 0", size_hint=(1, 0.05),
                                    font_size=16, color=(0.3, 1, 0.3, 1))
        self.received_data = TextInput(readonly=True, size_hint=(1, 0.6),
                                       background_color=(0, 1, 0, 0.1), foreground_color=(1, 1, 1, 1))
        
        self.input_field = TextInput(hint_text="Type your command here", size_hint=(1, 0.1),
                                     multiline=False, background_color=(0, 0.3, 0, 1),
                                     foreground_color=(1, 1, 1, 1), hint_text_color=(0.5, 1, 0.5, 1))
        self.input_field.bind(on_text_validate=self.handle_enter_key)

        self.sent_label = Label(text="Sent Commands", size_hint=(1, 0.05), font_size=16, color=(0, 1, 0, 1))
        self.sent_data = TextInput(readonly=True, size_hint=(1, 0.3),
                                   background_color=(0, 0.2, 0, 1), foreground_color=(1, 1, 1, 1))

        self.center_layout.add_widget(self.countdown_label)
        self.center_layout.add_widget(self.received_label)
        self.center_layout.add_widget(self.received_data)
        self.center_layout.add_widget(self.input_field)
        self.center_layout.add_widget(self.sent_label)
        self.center_layout.add_widget(self.sent_data)
        
        # Adattábla panel
        self.data_table = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        self.labels = []
        for i in range(15):
            label = Label(text=self.data_name_list[i], color=(0, 1, 0, 1), font_size=14)
            self.labels.append(label)
            self.data_table.add_widget(label)

        # Jobb oldali panel (Funkció gombok)
        self.right_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        for i in range(0, 8):
            btn = Button(text=self.button_names[i], font_size=14, background_color=(0, 0.5, 0, 1),
                         color=(1, 1, 1, 1), on_press=lambda x, cmd=i: self.send_cansat_kommand(cmd))
            self.right_layout.add_widget(btn)
            
        for i in range(8, 10):
            btn = Button(text=self.button_names[i], font_size=14, background_color=(0, 0.5, 0, 1),
                         color=(1, 1, 1, 1), on_press=lambda x, cmd=i: self.show_data(cmd))
            self.right_layout.add_widget(btn)
            
        self.toggle_2 = Button(text="lbt: OFF", font_size=14, background_color=(0, 0.5, 0, 1),
                               color=(1, 1, 1, 1), on_press=self.toggle_button_2)
        self.right_layout.add_widget(self.toggle_2)

        # Fő layout összerakása
        self.add_widget(self.left_layout)
        self.add_widget(self.center_layout)
        self.add_widget(self.data_table)
        self.add_widget(self.right_layout)

    # --- UI FRISSÍTŐ METÓDUSOK A FŐ SZÁLRA (Szálbiztos Kivy UI Módosítások) ---
    @mainthread
    def _ui_log_sent_command(self, command):
        self.sent_data.text += f"Sent: {command}\n"

    @mainthread
    def _ui_set_rx_color(self, color):
        self.received_data.background_color = color

    @mainthread
    def _ui_set_toggle_2_text(self, text):
        self.toggle_2.text = text
    # -------------------------------------------------------------------------

    def _init_matplotlib(self):
        """Matplotlib interaktív grafikon inicializálása"""
        plt.ion()
        self.fig, self.ax = plt.subplots()
        self.scatter = self.ax.scatter([], [], c='blue', label='ay vs Idő')
        self.ax.legend()
        plt.show(block=False)

    def _setup_radio_defaults(self):
        """Kezdeti rádió paraméterek beállítása"""
        commands = [
            "radio rxstop", "radio set bw 250", "radio set freq 864625000",
            "radio set sf sf9", "radio set pwr 14"
        ]
        # Külön szálon futtatjuk, de a UI frissítéseket a @mainthread fogja végezni
        def init_sequence():
            for cmd in commands:
                self.send_command(cmd)
                time.sleep(0.15)
        threading.Thread(target=init_sequence, daemon=True).start()

    def update_diagram(self, dt):
        """Matplotlib ábra frissítése (Biztonságos kivételkezeléssel)"""
        try:
            if len(self.all_data[0]) > 0 and len(self.all_data[4]) > 0:
                self.scatter.remove()
                self.scatter = self.ax.scatter(self.all_data[0], self.all_data[4], c='blue', label='ay vs Idő')
                self.ax.relim()
                self.ax.autoscale_view()
                self.fig.canvas.draw()
                self.fig.canvas.flush_events()
        except Exception as e:
            pass # Ha a grafikon be van zárva, ne crasheljen a program

    def show_data(self, cmd):
        if cmd == 8:
            self.received_data.text = ""
        if cmd == 9:
            if len(self.all_data[11]) > 0 and len(self.all_data[12]) > 0:
                base_url = "https://www.google.com/maps?q="
                link = f"{base_url}{self.all_data[11][-1]},{self.all_data[12][-1]}"
                webbrowser.open(link)
            else:
                self.received_data.text += "Nincs még GPS adat a térképhez.\n"

    def send_cansat_kommand(self, command):
        if not self.progress:
            self.flag = command   
            if command == 0:
                try:
                    self.package_rate = int(self.input_field.text) / 1000.0
                except ValueError:
                    pass
                     
            min_val = self.keyCansat[command][0]
            resolution = self.keyCansat[command][1]
            hex_char_num = self.keyCansat[command][2]
            
            try:
                new_val = float(self.input_field.text)
                new_val_scaled = round((new_val - min_val) * (1 / resolution))
                
                send_cmd = f"radio tx {command+1}{hex(new_val_scaled)[2:].zfill(hex_char_num)} 1"
                self.send_command(send_cmd)
                self.input_field.hint_text = "Parancs elküldve"
                self.input_field.text = ""
            except ValueError:
                self.input_field.hint_text = "Hiba: Először adj meg egy számot!"

    def send_command(self, command):
        # UI frissítések a biztonságos @mainthread függvényeken keresztül
        if command == "radio rx 0":
            self._ui_set_rx_color((0, 1, 0, 0.5))
        elif command == "radio rxstop":
            self._ui_set_rx_color((0, 1, 0, 0.1))
            
        if self.serial_port and self.serial_port.is_open:
            if "radio tx" in command:
                self._write_serial("radio rxstop")
                time.sleep(0.1)

            self._write_serial(command)
            self._ui_log_sent_command(command)

            if "radio tx" in command:
                time.sleep(0.08)
                self._write_serial("radio rx 0")

    def _write_serial(self, command):
        data_to_send = command + "\r\n"
        print(f"Elküldve: {data_to_send.strip()}")
        self.serial_port.write(data_to_send.encode('utf-8'))

    def send_command_part(self, command):
        self.input_field.text = command
        print(command)

    def handle_enter_key(self, instance):
        command = self.input_field.text.strip()
        if command:
            self.send_command(command)
            self.input_field.text = ""

    def toggle_button_1(self, instance):
        if "OFF" in self.toggle_1.text:
            self.toggle_1.text = "snr: ON"
            self.toggle_1.background_color = (0, 0.8, 0, 1)
            self.snr = True
        else:
            self.toggle_1.text = "snr: OFF"
            self.toggle_1.background_color = (0, 0.1, 0, 1)
            self.snr = False

    def toggle_button_2(self, instance):
        # Lekérjük az állapotot még a főszálon, hogy ne a threads-ből kelljen kiolvasni
        is_off = "OFF" in self.toggle_2.text
        
        # Ezt külön szálon futtatjuk, hogy a time.sleep ne fagyassza ki a Kivy-t
        def lbt_toggle_thread():
            if is_off:
                self._ui_set_toggle_2_text("lbt: ON")
                self.send_command("radio rxstop")
                time.sleep(0.1)
                self.send_command("radio set lbt 5 -80 10 1")
                time.sleep(0.1)
                self.send_command("radio rx 0")
            else:
                self._ui_set_toggle_2_text("lbt: OFF")
                self.send_command("radio rxstop")
                time.sleep(0.1)
                self.send_command("radio set lbt 5 -80 10 0")
                time.sleep(0.1)
                self.send_command("radio rx 0")
                
        threading.Thread(target=lbt_toggle_thread, daemon=True).start()

    def toggle_button_3(self, instance):
        if "OFF" in self.toggle_3.text:
            self.toggle_3.text = "pktrssi: ON"
            self.pktrssi = True
            self.toggle_3.background_color = (0, 0.8, 0, 1)
        else:
            self.toggle_3.text = "pktrssi: OFF"
            self.toggle_3.background_color = (0, 0.1, 0, 1)
            self.pktrssi = False

    def update_countdown(self, dt):
        self.countdown_time -= dt
        if self.countdown_time <= -0.2:
            self.countdown_time = self.package_rate
            try:
                misses = int(self.received_label.text.split(":")[-1])
                self.received_label.text = f"Received Data, miss: {misses + 1}"
            except ValueError:
                pass
        self.countdown_label.text = f"Countdown: {self.countdown_time:.1f}"

    def read_from_uart(self, dt):
        """Adatok olvasása és mentése"""
        if self.serial_port and self.serial_port.is_open and self.serial_port.in_waiting > 0:
            try:
                data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8').strip()
                if data:
                    if data.startswith("radio_rx"):
                        if data == "radio_rx ff":
                            self.progress = False
                            self.send_command("radio rxstop")
                            time.sleep(0.1)
                            
                            # Parancs nyugtázása
                            if self.flag == 1:
                                self.send_command(f"{self.comf_b1[self.flag]}{int(self.input_field.text)*1000}")
                            elif 1 < self.flag < 5:
                                self.send_command(f"{self.comf_b1[self.flag]}{self.input_field.text}")
                                
                            self.received_data.text += "comf. sucessful\n"
                            time.sleep(0.01)
                            self.send_command("radio rx 0")
                                
                        elif len(data) >= 79:  # Telemetria csomag
                            self.countdown_time = self.package_rate
                            self.received_label.text = "Received Data, miss: 0"
                            fields = data.split(' ')
                            hexek_be = fields[1] 
                            
                            for i in range(14):
                                hex_be = int(hexek_be[self.key[i]:self.key[i+1]], 16)

                                if hex_be == 0:
                                    valute = None
                                else:
                                    valute = round(self.keydata[i][2] * hex_be + self.keydata[i][0], 4)
                                    if i == 0:
                                        valute = valute / 10.0
                                        if len(self.all_data[0]) > 0 and abs(self.all_data[0][-1] - valute) > 2000:
                                            valute = None
                                            print("Időbélyeg ugrás hiba (error)")
                                            
                                    if i == 11 or i == 12: # GPS átváltás
                                        val_str = str(valute)
                                        if len(val_str) > 2:
                                            valute = round(int(val_str[:2]) + float(val_str[2:]) / 60, 6)
                                    
                                self.all_data[i].append(valute)
                                self.labels[i].text = f"{self.data_name_list[i]}: {valute}"
                                
                            # Magasság számítása nyomás alapján
                            if len(self.all_data[2]) > 0 and len(self.all_data[1]) > 0:
                                last_pressure = self.all_data[2][-1]
                                last_temp = self.all_data[1][-1]
                                if last_pressure and last_temp:
                                    alt_calc = round(- (pow(last_pressure / 1018.95, 1 / (9.81 * 0.029 / 8.31447 / 0.0065)) - 1) * (last_temp + 273) / 0.0065, 2)
                                    self.all_data[14].append(alt_calc)
                                    self.labels[14].text = f"{self.data_name_list[14]}: {alt_calc}"

                            # BIZTONSÁGOS FÁJLMENTÉS (Context Manager)
                            with open("g_safe.txt", "a", encoding="utf-8") as fg:
                                fg.write(f"{self.all_data},\n")

                            # SNR és RSSI lekérdezése
                            if self.snr:
                                self._write_serial("radio get snr")
                                snr_data = self.serial_port.readline().decode('utf-8').strip()
                                with open("g_pktrssi.txt", "a", encoding="utf-8") as fs:
                                    fs.write(f"{snr_data},\n")
                                self.received_data.text += f"snr : {snr_data}\n"
                                
                            if self.pktrssi:
                                self._write_serial("radio get pktrssi")
                                rssi_data = self.serial_port.readline().decode('utf-8').strip()
                                with open("g_pktrssi.txt", "a", encoding="utf-8") as fp:
                                    fp.write(f"{rssi_data},\n")
                                self.received_data.text += f"pktrssi : {rssi_data}\n"

                    else:
                        print(f"Ismeretlen csomag: {data}")

            except Exception as e:
                print(f"Hiba az UART olvasása közben: {e}")

class UARTGUIApp(App):
    def build(self):
        return UARTApp()

if __name__ == '__main__':
    UARTGUIApp().run()