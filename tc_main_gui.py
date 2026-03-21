#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleClinic Bot - Haupt-GUI mit integriertem Scanner & Clicker
Startet Scanner und Clicker automatisch mit den gewählten Filtern
MIT LIZENZ-SCHUTZ (Hardware-Bindung)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import json
import asyncio
import threading
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

ROOT_PATH = Path(__file__).resolve().parent
FILTER_PATH = ROOT_PATH / "filters.json"
LOG_PATH = ROOT_PATH / "tc_click_log.txt"

# Importiere Lizenz-System (falls vorhanden)
check_license_before_start = None
try:
    from license_system import check_license_before_start
    LICENSE_SYSTEM_AVAILABLE = True
except ImportError:
    LICENSE_SYSTEM_AVAILABLE = False
    print("⚠️ Lizenz-System nicht verfügbar - läuft ohne Schutz")

class TeleClinicBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 TeleClinic Bot - Hauptprogramm")
        self.root.geometry("1000x700")
        self.root.resizable(True, True)

        self.bot_process = None  # Speichere Prozess-Handle
        self.is_running = False
        self.monitor_thread = None

        self.setup_ui()
        self.load_filters()

    def setup_ui(self):
        """Erstelle die GUI"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # Titel mit Logo/Grafik
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=15)
        title_frame.columnconfigure(1, weight=1)  # Mittlerer Bereich expandiert

        # Bot-Emoji links vor dem Titel
        bot_label = ttk.Label(title_frame, text="🤖", font=("Arial", 32))
        bot_label.pack(side="left", padx=(5, 10))

        # Titel neben dem TeleClinic-Bot Emoji
        title = ttk.Label(title_frame, text="TeleClinic AutoBot\nAutomatische Terminvergabe",
                         font=("Arial", 16, "bold"))
        title.pack(side="left", padx=10)

        # Spacer für Flexibilität
        spacer = ttk.Frame(title_frame)
        spacer.pack(side="left", fill="both", expand=True)

        # Lade und zeige Praxislogo rechts
        try:
            logo_path = ROOT_PATH / "Logo_GIZ_Praxis_neu_ohne_Hintergrund.png"
            if logo_path.exists():
                # Lade Bild
                img = Image.open(logo_path)
                # Resize auf angemessene Größe (Höhe 60 Pixel, proportional)
                img.thumbnail((150, 60), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)

                # Zeige Logo
                logo_label = ttk.Label(title_frame, image=self.logo_image)
                logo_label.pack(side="right", padx=10)
            else:
                # Fallback: Emoji, falls Datei nicht existiert
                emoji_label = ttk.Label(title_frame, text="🏥", font=("Arial", 40))
                emoji_label.pack(side="right", padx=10)
        except Exception as e:
            # Fallback bei Fehler
            print(f"Fehler beim Laden des Logos: {e}")
            emoji_label = ttk.Label(title_frame, text="🏥", font=("Arial", 40))
            emoji_label.pack(side="right", padx=10)

        # --- FILTER-BEREICH ---
        filter_frame = ttk.LabelFrame(main_frame, text="Filter", padding="10")
        filter_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=10)
        filter_frame.columnconfigure(1, weight=1)

        pad = {"padx": 5, "pady": 5}

        # Tag
        ttk.Label(filter_frame, text="Tag").grid(row=0, column=0, sticky="w", **pad)
        self.day_window = ttk.Combobox(filter_frame, values=["heute", "morgen", "später"], state="readonly")
        self.day_window.set("heute")
        self.day_window.grid(row=0, column=1, sticky="ew", **pad)

        # Zeit
        ttk.Label(filter_frame, text="Zeit von").grid(row=1, column=0, sticky="w", **pad)
        self.time_from = ttk.Entry(filter_frame, width=10)
        self.time_from.insert(0, "21:30")
        self.time_from.grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(filter_frame, text="bis").grid(row=1, column=2, sticky="w", **pad)
        self.time_to = ttk.Entry(filter_frame, width=10)
        self.time_to.insert(0, "23:30")
        self.time_to.grid(row=1, column=3, sticky="w", **pad)

        # Alter
        ttk.Label(filter_frame, text="Alter min").grid(row=2, column=0, sticky="w", **pad)
        self.age_min = ttk.Entry(filter_frame, width=10)
        self.age_min.insert(0, "")
        self.age_min.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(filter_frame, text="max").grid(row=2, column=2, sticky="w", **pad)
        self.age_max = ttk.Entry(filter_frame, width=10)
        self.age_max.insert(0, "")
        self.age_max.grid(row=2, column=3, sticky="w", **pad)

        # Geschlecht
        ttk.Label(filter_frame, text="Geschlecht").grid(row=3, column=0, sticky="w", **pad)
        self.gender = ttk.Combobox(filter_frame, values=["egal", "männlich", "weiblich", "divers"], state="readonly", width=15)
        self.gender.set("egal")
        self.gender.grid(row=3, column=1, sticky="w", **pad)

        # Diagnose (Include)
        ttk.Label(filter_frame, text="Diagnose").grid(row=4, column=0, sticky="w", **pad)
        self.diagnosis = ttk.Entry(filter_frame, width=30)
        self.diagnosis.insert(0, "")
        self.diagnosis.grid(row=4, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche (Include)
        ttk.Label(filter_frame, text="Wünsche (AU,Rezept)").grid(row=5, column=0, sticky="w", **pad)
        self.wishes = ttk.Entry(filter_frame, width=30)
        self.wishes.insert(0, "")
        self.wishes.grid(row=5, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache (Include)
        ttk.Label(filter_frame, text="Sprache").grid(row=6, column=0, sticky="w", **pad)
        self.language = ttk.Entry(filter_frame, width=30)
        self.language.insert(0, "")
        self.language.grid(row=6, column=1, columnspan=2, sticky="ew", **pad)

        # Diagnose ausschließen (Exclude)
        ttk.Label(filter_frame, text="Diagnose ausschließen").grid(row=7, column=0, sticky="w", **pad)
        self.diagnosis_exclude = ttk.Entry(filter_frame, width=30)
        self.diagnosis_exclude.insert(0, "")
        self.diagnosis_exclude.grid(row=7, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche ausschließen (Exclude)
        ttk.Label(filter_frame, text="Wünsche ausschließen").grid(row=8, column=0, sticky="w", **pad)
        self.wishes_exclude = ttk.Entry(filter_frame, width=30)
        self.wishes_exclude.insert(0, "")
        self.wishes_exclude.grid(row=8, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache ausschließen (Exclude)
        ttk.Label(filter_frame, text="Sprache ausschließen").grid(row=9, column=0, sticky="w", **pad)
        self.language_exclude = ttk.Entry(filter_frame, width=30)
        self.language_exclude.insert(0, "")
        self.language_exclude.grid(row=9, column=1, columnspan=2, sticky="ew", **pad)

        # Max Patienten
        ttk.Label(filter_frame, text="Max Patienten").grid(row=10, column=0, sticky="w", **pad)
        self.max_patients = ttk.Spinbox(filter_frame, from_=1, to=20, width=10)
        self.max_patients.set(5)
        self.max_patients.grid(row=10, column=1, sticky="w", **pad)

        # Loop-Geschwindigkeit (Scan-Intervall)
        ttk.Label(filter_frame, text="Scan-Intervall (Sek)").grid(row=11, column=0, sticky="w", **pad)
        self.scan_interval = ttk.Spinbox(filter_frame, from_=1, to=30, width=10)
        self.scan_interval.set(8)
        self.scan_interval.grid(row=11, column=1, sticky="w", **pad)

        # Behandlungsintervall (Minuten)
        ttk.Label(filter_frame, text="Behandlungsintervall (Min)").grid(row=11, column=2, sticky="w", **pad)
        self.interval_minutes = ttk.Spinbox(filter_frame, from_=1, to=60, width=10)
        self.interval_minutes.set(5)
        self.interval_minutes.grid(row=11, column=3, sticky="w", **pad)

        # Max Seiten
        ttk.Label(filter_frame, text="Max Seiten").grid(row=12, column=0, sticky="w", **pad)
        self.max_pages = ttk.Spinbox(filter_frame, from_=1, to=20, width=10)
        self.max_pages.set(5)
        self.max_pages.grid(row=12, column=1, sticky="w", **pad)

        # --- BUTTON-BEREICH ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

        self.start_btn = ttk.Button(button_frame, text="▶️ START - Scanner & Clicker",
                                   command=self.start_bot)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(button_frame, text="⏹️ STOP",
                                  command=self.stop_bot, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        ttk.Button(button_frame, text="💾 Filter speichern",
                  command=self.save_filters).pack(side="left", padx=5)

        ttk.Button(button_frame, text="❌ Programm beenden",
                  command=self.exit_app).pack(side="right", padx=5)

        # --- STATUS/LOG-BEREICH ---
        log_frame = ttk.LabelFrame(main_frame, text="Live-Log", padding="10")
        log_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=10)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=80,
                                                  state="disabled", wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")

        # --- TERMINKALENDER-BEREICH (NEU) ---
        calendar_frame = ttk.LabelFrame(main_frame, text="📅 Terminkalender - Übersicht", padding="5")
        calendar_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=5)
        calendar_frame.rowconfigure(0, weight=1)
        calendar_frame.columnconfigure(0, weight=1)

        # Treeview für Termine
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        self.appointment_tree = ttk.Treeview(
            calendar_frame,
            columns=("Uhrzeit", "Diagnose", "Wunsch", "Alter", "Geschlecht"),
            height=6,
            show="headings"
        )

        # Definiere Spalten
        self.appointment_tree.heading("#0", text="Nr.")
        self.appointment_tree.heading("Uhrzeit", text="⏰ Uhrzeit")
        self.appointment_tree.heading("Diagnose", text="📋 Diagnose")
        self.appointment_tree.heading("Wunsch", text="💊 Wunsch")
        self.appointment_tree.heading("Alter", text="👤 Alter")
        self.appointment_tree.heading("Geschlecht", text="👥 Geschlecht")

        self.appointment_tree.column("#0", width=40)
        self.appointment_tree.column("Uhrzeit", width=80)
        self.appointment_tree.column("Diagnose", width=120)
        self.appointment_tree.column("Wunsch", width=100)
        self.appointment_tree.column("Alter", width=60)
        self.appointment_tree.column("Geschlecht", width=80)

        # Scrollbar für Treeview
        scrollbar = ttk.Scrollbar(calendar_frame, orient="vertical", command=self.appointment_tree.yview)
        self.appointment_tree.configure(yscrollcommand=scrollbar.set)

        self.appointment_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Status-Label
        self.status_label = ttk.Label(main_frame, text="Status: Bereit",
                                     font=("Arial", 10))
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=5)

    def load_filters(self):
        """Lade gespeicherte Filter"""
        if FILTER_PATH.exists():
            try:
                with open(FILTER_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.day_window.set(data.get("time_filter", {}).get("day_window", "heute"))
                    self.time_from.delete(0, tk.END)
                    self.time_from.insert(0, data.get("time_filter", {}).get("treatment_start", "21:30"))
                    self.time_to.delete(0, tk.END)
                    self.time_to.insert(0, data.get("time_filter", {}).get("treatment_end", "23:30"))
                    self.age_min.delete(0, tk.END)
                    self.age_min.insert(0, str(data.get("patients", {}).get("age_min", "")))
                    self.age_max.delete(0, tk.END)
                    self.age_max.insert(0, str(data.get("patients", {}).get("age_max", "")))
                    self.gender.set(data.get("patients", {}).get("gender", "egal"))
                    self.language.delete(0, tk.END)
                    lang = data.get("patients", {}).get("language_include", [])
                    self.language.insert(0, ",".join(lang) if isinstance(lang, list) else "")
                    self.language_exclude.delete(0, tk.END)
                    lang_excl = data.get("patients", {}).get("language_exclude", [])
                    self.language_exclude.insert(0, ",".join(lang_excl) if isinstance(lang_excl, list) else "")
                    self.diagnosis.delete(0, tk.END)
                    diag = data.get("diagnosis", {}).get("include", "")
                    self.diagnosis.insert(0, diag if isinstance(diag, str) else ",".join(diag))
                    self.diagnosis_exclude.delete(0, tk.END)
                    diag_excl = data.get("diagnosis", {}).get("exclude", "")
                    self.diagnosis_exclude.insert(0, diag_excl if isinstance(diag_excl, str) else ",".join(diag_excl))
                    self.wishes.delete(0, tk.END)
                    wish = data.get("wishes", {}).get("include", "")
                    self.wishes.insert(0, wish if isinstance(wish, str) else ",".join(wish))
                    self.wishes_exclude.delete(0, tk.END)
                    wish_excl = data.get("wishes", {}).get("exclude", "")
                    self.wishes_exclude.insert(0, wish_excl if isinstance(wish_excl, str) else ",".join(wish_excl))
                    self.max_patients.set(data.get("runtime", {}).get("max_patients", 5))
                    self.scan_interval.set(data.get("loop", {}).get("scan_interval_sec", 8))
                    # NEU: interval_minutes laden
                    self.interval_minutes.set(data.get("runtime", {}).get("interval_minutes", 5))
                    self.max_pages.set(data.get("loop", {}).get("max_pages", 5))
            except Exception as e:
                self.log("⚠️ Fehler beim Laden der Filter: " + str(e))

    def save_filters(self):
        """Speichere Filter in filters.json"""
        # Interval-Minuten Default 5, falls leer/ungültig
        try:
            interval_min = int(self.interval_minutes.get()) if str(self.interval_minutes.get()).strip().isdigit() else 5
        except Exception:
            interval_min = 5
        data = {
            "time_filter": {
                "day_window": self.day_window.get(),
                "treatment_start": self.time_from.get(),
                "treatment_end": self.time_to.get()
            },
            "runtime": {
                "interval_minutes": interval_min,
                "max_patients": int(self.max_patients.get()),
                "headless": False,
                "slowmo_ms": 0
            },
            "patients": {
                "gender": self.gender.get() if self.gender.get() != "egal" else "",
                "age_min": int(self.age_min.get()) if self.age_min.get().strip().isdigit() else "",
                "age_max": int(self.age_max.get()) if self.age_max.get().strip().isdigit() else "",
                "language_include": [x.strip() for x in self.language.get().split(",") if x.strip()],
                "language_exclude": [x.strip() for x in self.language_exclude.get().split(",") if x.strip()]
            },
            "diagnosis": {
                "include": self.diagnosis.get().strip(),
                "exclude": self.diagnosis_exclude.get().strip()
            },
            "wishes": {
                "include": self.wishes.get().strip(),
                "exclude": self.wishes_exclude.get().strip()
            },
            "loop": {
                "scan_interval_sec": int(self.scan_interval.get()),
                "max_pages": int(self.max_pages.get())
            }
        }
        try:
            with open(FILTER_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log("✅ Filter gespeichert!")
            messagebox.showinfo("Erfolg", "Filter wurden gespeichert.")
        except Exception as e:
            self.log("❌ Fehler beim Speichern: " + str(e))
            messagebox.showerror("Fehler", "Filter konnten nicht gespeichert werden.")

    def log(self, message: str):
        """Schreibe in Log-Bereich"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        print(line)

    def start_bot(self):
        """Starte Scanner & Clicker"""
        self.save_filters()

        # Zeige Filter-Übersicht
        self.log("=" * 80)
        self.log("🚀 STARTE BOT - SCANNER & CLICKER")
        self.log("=" * 80)
        self.log(f"📅 TAG: {self.day_window.get()}")
        self.log(f"🕐 ZEIT: {self.time_from.get()} - {self.time_to.get()}")
        self.log(f"📋 DIAGNOSE: {self.diagnosis.get() or '(egal)'}")

        wishes_str = self.wishes.get() or '(keine)'
        self.log(f"💊 WÜNSCHE: {wishes_str}")

        gender_str = self.gender.get() if self.gender.get() != "egal" else "(egal)"
        age_str = ""
        if self.age_min.get().strip():
            age_str += f"{self.age_min.get()}"
        if self.age_max.get().strip():
            if age_str:
                age_str += f"-{self.age_max.get()}"
            else:
                age_str = f"bis {self.age_max.get()}"
        if not age_str:
            age_str = "(egal)"
        self.log(f"👤 GESCHLECHT: {gender_str} | ALTER: {age_str}")

        self.log(f"👥 MAX PATIENTEN: {self.max_patients.get()}")
        self.log(f"🔁 INTERVALL: {self.interval_minutes.get()} Min | ⏱️ SCAN: {self.scan_interval.get()} s | 📄 Seiten: {self.max_pages.get()}")
        self.log("=" * 80)
        self.log("")

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="Status: 🟢 Bot läuft...")

        # Starte Bot in separatem Thread
        thread = threading.Thread(target=self._run_bot, daemon=True)
        thread.start()

        # Starte Monitor-Thread
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self._monitor_log, daemon=True)
            self.monitor_thread.start()

    def _run_bot(self):
        """Führe Bot aus"""
        try:
            if getattr(sys, 'frozen', False):
                self.log("[INFO] Starte Scanner im EXE-Modus...")
                from teleclinic_click_from_list_v9d import main as clicker_main
                asyncio.run(clicker_main())
                return_code = 0
            else:
                # Starte Bot als Subprocess und speichere Prozess-Handle
                self.bot_process = subprocess.Popen(
                    [sys.executable, str(ROOT_PATH / "teleclinic_click_from_list_v9d.py")],
                    cwd=str(ROOT_PATH)
                )

                # Warte auf Prozess-Ende
                return_code = self.bot_process.wait()
            self.log(f"✅ Bot beendet (Exit-Code: {return_code})")
        except Exception as e:
            self.log(f"❌ Fehler beim Starten des Bots: {e}")
        finally:
            self.is_running = False
            self.bot_process = None
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status_label.config(text="Status: 🔴 Bot beendet")

    def _monitor_log(self):
        """
        Überwache Log-Datei und zeige:
        - Scan-Status (läuft gerade)
        - Terminierte Fälle (nummeriert mit Zeit)
        - Aktualisiere Terminkalender
        """
        last_pos = 0
        terminated_count = 0
        last_calendar_update = time.time()  # Für regelmäßige Updates

        while self.is_running:
            try:
                if LOG_PATH.exists():
                    with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                        for line in new_lines:
                            line = line.strip()
                            if not line:
                                continue

                            # Zeige nur relevante Zeilen
                            show_line = False
                            formatted_line = line

                            # 1. Scan-Status: "Scanne Seite X"
                            if "[SCAN] Scanne Seite" in line:
                                if "Anfragen gefunden" in line:
                                    show_line = True
                                    formatted_line = f"🔄 {line}"

                            # 2. Terminierte Fälle - MEHRERE TRIGGER FÜR ROBUSTHEIT
                            # Erkenne: "[OK] Anfrage übernommen" ODER "[OK] Anfrage bernommen" (Encoding-Problem)
                            # ODER "[OK] Termin XX:XX eingetragen" (früherer Trigger)
                            elif (("[OK]" in line and ("bernommen" in line or "übernommen" in line)) or
                                  ("[OK] Termin" in line and "eingetragen" in line) or
                                  "✅ Fall" in line):
                                terminated_count += 1
                                show_line = True
                                formatted_line = f"[{terminated_count}] ✅ {line}"

                                # WICHTIG: Sofortige Terminkalender-Aktualisierung mit neuer Methode!
                                self._update_calendar_from_json()
                                last_calendar_update = time.time()

                            # 3. Wichtige Fehler
                            elif "❌" in line and "Fehler" in line:
                                show_line = True
                                formatted_line = f"⚠️ {line}"

                            # 4. Bot beendet
                            elif "Maximale Patientenanzahl erreicht" in line or "SHUTDOWN" in line:
                                show_line = True
                                formatted_line = f"🛑 {line}"

                            if show_line:
                                self.log_text.config(state="normal")
                                self.log_text.insert("end", formatted_line + "\n")
                                self.log_text.see("end")
                                self.log_text.config(state="disabled")

                                # Prüfe auf Beende-Bedingungen
                                if "Maximale Patientenanzahl erreicht" in line:
                                    self.log("🎯 Maximale Patientenzahl erreicht - beende Bot!")
                                    self.is_running = False
                                    # Beende Prozess aktiv
                                    if self.bot_process and self.bot_process.poll() is None:
                                        self.bot_process.terminate()
                                        try:
                                            self.bot_process.wait(timeout=3)
                                        except subprocess.TimeoutExpired:
                                            self.bot_process.kill()
                                    break

                # Regelmäßige Terminkalender-Aktualisierung (alle 2 Sekunden)
                # Falls Log-Zeilen verpasst wurden oder Datei extern geändert wurde
                current_time = time.time()
                if current_time - last_calendar_update >= 2.0:
                    self._update_calendar_from_json()
                    last_calendar_update = current_time

                time.sleep(0.5)
            except Exception as e:
                time.sleep(1)

    def _update_calendar_from_json(self):
        """
        Lade ALLE Termine direkt aus scheduled_patients.json und aktualisiere den Kalender.
        Diese Methode liest die JSON-Datei KOMPLETT neu bei jedem Aufruf.
        """
        try:
            from scheduled_patients import get_patients_for_date
            from datetime import datetime, timedelta

            # Bestimme das RICHTIGE Datum basierend auf dem Scanner-Filter
            day_window = self.day_window.get() if hasattr(self, 'day_window') else "heute"

            if day_window == "morgen":
                target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif day_window == "später":
                target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            else:
                target_date = datetime.now().strftime("%Y-%m-%d")

            # Lade ALLE Patienten für das richtige Datum
            patients = get_patients_for_date(target_date)

            # Lösche alte Einträge im Terminkalender
            for item in self.appointment_tree.get_children():
                self.appointment_tree.delete(item)

            if patients:
                # Sortiere nach Zeit
                sorted_times = sorted(patients.keys())

                # Füge JEDEN Patienten einzeln hinzu
                for idx, time_slot in enumerate(sorted_times, 1):
                    patient = patients[time_slot]

                    # Extrahiere Patientendaten
                    uhrzeit = time_slot
                    diagnose = patient.get("diagnosis", "(unbekannt)")
                    wunsch = patient.get("wishes", "(keine)")
                    alter = str(patient.get("age", "(egal)"))
                    geschlecht = patient.get("gender", "(egal)")

                    # Bereinige leere Felder
                    if not diagnose or diagnose.strip() == "":
                        diagnose = "(unbekannt)"
                    if not wunsch or wunsch.strip() == "":
                        wunsch = "(keine)"
                    if not alter or alter.strip() == "":
                        alter = "(egal)"
                    if not geschlecht or geschlecht.strip() == "":
                        geschlecht = "(egal)"

                    # Kürze lange Texte
                    diagnose = diagnose[:30]
                    wunsch = wunsch[:30]
                    alter = alter[:20]
                    geschlecht = geschlecht[:15]

                    # Füge zum Terminkalender hinzu
                    self.appointment_tree.insert("", "end", text=str(idx), values=(
                        uhrzeit,
                        diagnose,
                        wunsch,
                        alter,
                        geschlecht
                    ))

        except ImportError:
            # scheduled_patients Modul nicht vorhanden
            pass
        except Exception as e:
            print(f"[ERROR] Fehler beim Aktualisieren des Kalenders: {e}")
            import traceback
            traceback.print_exc()

    def stop_bot(self):
        """Stoppe Bot"""
        self.log("⏹️ Stoppe Bot...")
        self.is_running = False

        # Falls der Clicker-Prozess noch läuft, sauber beenden
        if self.bot_process and self.bot_process.poll() is None:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
            self.log("🛑 Bot-Prozess beendet.")
        self.bot_process = None

        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Status: 🔴 Bot gestoppt")

    def exit_app(self):
        """Beende Anwendung"""
        if self.is_running:
            response = messagebox.askyesno("Bestätigung",
                "Bot läuft noch. Wirklich beenden?")
            if not response:
                return
            self.stop_bot()
        self.root.quit()
        sys.exit(0)


def main():
    # Prüfe Lizenz BEVOR GUI startet
    if LICENSE_SYSTEM_AVAILABLE:
        print("Prüfe Lizenz...")
        if not check_license_before_start(debug=True):
            print("[ERROR] Keine gültige Lizenz - Programm wird beendet")
            sys.exit(1)
        print("[INFO] Lizenz OK - Starte GUI")

    root = tk.Tk()
    app = TeleClinicBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
