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


def migrate_filters_to_slot_format(data: dict) -> dict:
    """
    Migriert alte filters.json (ein Filterset) zu neuem Format (slot1 + slot2).

    Alt: time_filter + diagnosis + patients + wishes (alle zusammen)
    Neu: slot1 { time_start, time_end, max_patients, diagnosis_include, ... }
         slot2_enabled: false (oder true wenn slot2 Daten existieren)
         slot2 { ... }

    Abwärtskompatibel: Alte Daten werden in slot1 kopiert, slot2_enabled = false.
    """
    # Prüfe ob bereits neues Format
    if "slot1" in data and "slot2_enabled" in data:
        return data  # Bereits neu

    # Alte Struktur in neue konvertieren
    time_filter = data.get("time_filter", {})
    runtime = data.get("runtime", {})
    patients = data.get("patients", {})
    diagnosis = data.get("diagnosis", {})
    wishes = data.get("wishes", {})
    loop = data.get("loop", {})

    new_data = {
        "time_filter": {
            "day_window": time_filter.get("day_window", "heute")
        },
        "slot1": {
            "time_start": time_filter.get("treatment_start", "21:30"),
            "time_end": time_filter.get("treatment_end", "23:30"),
            "max_patients": runtime.get("max_patients", 5),
            "interval_minutes": runtime.get("interval_minutes", 5),
            "diagnosis_include": diagnosis.get("include", ""),
            "diagnosis_exclude": diagnosis.get("exclude", ""),
            "wishes_include": wishes.get("include", ""),
            "wishes_exclude": wishes.get("exclude", ""),
            "language_include": ",".join(patients.get("language_include", [])) if isinstance(patients.get("language_include"), list) else patients.get("language_include", ""),
            "language_exclude": ",".join(patients.get("language_exclude", [])) if isinstance(patients.get("language_exclude"), list) else patients.get("language_exclude", ""),
            "age_min": str(patients.get("age_min", "")),
            "age_max": str(patients.get("age_max", "")),
            "gender": patients.get("gender", "")
        },
        "slot2_enabled": False,
        "slot2": {
            "time_start": time_filter.get("treatment_start_2", ""),
            "time_end": time_filter.get("treatment_end_2", ""),
            "max_patients": 5,
            "interval_minutes": runtime.get("interval_minutes", 5),
            "diagnosis_include": "",
            "diagnosis_exclude": "",
            "wishes_include": "",
            "wishes_exclude": "",
            "language_include": "",
            "language_exclude": "",
            "age_min": "",
            "age_max": "",
            "gender": ""
        },
        "runtime": {
            "interval_minutes": runtime.get("interval_minutes", 5),
            "headless": runtime.get("headless", False),
            "slowmo_ms": runtime.get("slowmo_ms", 0)
        },
        "loop": {
            "scan_interval_sec": loop.get("scan_interval_sec", 5),
            "max_pages": loop.get("max_pages", 5)
        }
    }

    return new_data

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
        # Zeile 0 = Titel (fix), Zeile 1 = scrollbarer Bereich (flex), Zeile 2 = Buttons (fix), Zeile 3/4 = Log/Kalender
        main_frame.rowconfigure(1, weight=1)

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
        # Reihenfolge: GIZ-Logo → TeleClinic-Scanner-Logo → Text-Fallback
        _logo_candidates = [
            ROOT_PATH / "Logo_GIZ_Praxis_neu_ohne_Hintergrund.png",
            ROOT_PATH / "Logo Teleclinic scanner.png",
            ROOT_PATH / "Logo Teleclinic.png",
        ]
        _logo_loaded = False
        for logo_path in _logo_candidates:
            try:
                # Datei muss existieren UND Inhalt haben (> 0 Bytes)
                if not logo_path.exists() or logo_path.stat().st_size == 0:
                    continue
                img = Image.open(logo_path)
                img.verify()          # prüft ob PNG-Struktur intakt ist
                img = Image.open(logo_path)   # nach verify() neu öffnen
                img.thumbnail((150, 60), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
                logo_label = ttk.Label(title_frame, image=self.logo_image)
                logo_label.pack(side="right", padx=10)
                _logo_loaded = True
                break
            except Exception as e:
                print(f"[Logo] '{logo_path.name}' übersprungen: {e}")
                continue

        if not _logo_loaded:
            # Text-Fallback: sauberes Label statt defektem Bild
            fallback_label = ttk.Label(title_frame, text="GIZ Praxis",
                                       font=("Arial", 11, "bold"), foreground="#1a5276")
            fallback_label.pack(side="right", padx=10)

        # --- SCROLLBARER FILTER-BEREICH ---
        # Canvas + Scrollbar als Container für den Filter-Bereich
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=5)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.filter_canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        scrollbar_v = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.filter_canvas.yview)
        self.filter_canvas.configure(yscrollcommand=scrollbar_v.set)

        scrollbar_v.grid(row=0, column=1, sticky="ns")
        self.filter_canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbar mit Mausrad verbinden
        self.filter_canvas.bind("<Enter>", lambda e: self.filter_canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.filter_canvas.bind("<Leave>", lambda e: self.filter_canvas.unbind_all("<MouseWheel>"))

        # Innerer Frame im Canvas
        self.scroll_inner = ttk.Frame(self.filter_canvas)
        self.canvas_window = self.filter_canvas.create_window((0, 0), window=self.scroll_inner, anchor="nw")

        self.scroll_inner.bind("<Configure>", self._on_frame_configure)
        self.filter_canvas.bind("<Configure>", self._on_canvas_configure)

        # Ab jetzt alle Filter in self.scroll_inner platzieren
        filter_frame = ttk.LabelFrame(self.scroll_inner, text="Filter", padding="10")
        filter_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
        filter_frame.columnconfigure(1, weight=1)

        pad = {"padx": 5, "pady": 3}

        # ===== SLOT 1 =====
        slot1_label = ttk.Label(filter_frame, text="🕐 SLOT 1", font=("Arial", 10, "bold"))
        slot1_label.grid(row=0, column=0, columnspan=4, sticky="w", **pad)

        # Tag (global)
        ttk.Label(filter_frame, text="Tag").grid(row=1, column=0, sticky="w", **pad)
        self.day_window = ttk.Combobox(filter_frame, values=["heute", "morgen", "später"], state="readonly")
        self.day_window.set("heute")
        self.day_window.grid(row=1, column=1, sticky="ew", **pad)

        # Zeit Slot 1
        ttk.Label(filter_frame, text="Zeit von").grid(row=2, column=0, sticky="w", **pad)
        self.time_from = ttk.Entry(filter_frame, width=10)
        self.time_from.insert(0, "21:30")
        self.time_from.grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(filter_frame, text="bis").grid(row=2, column=2, sticky="w", **pad)
        self.time_to = ttk.Entry(filter_frame, width=10)
        self.time_to.insert(0, "23:30")
        self.time_to.grid(row=2, column=3, sticky="w", **pad)

        # Diagnose (Slot 1)
        ttk.Label(filter_frame, text="Diagnose").grid(row=3, column=0, sticky="w", **pad)
        self.diagnosis = ttk.Entry(filter_frame, width=30)
        self.diagnosis.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche (Slot 1)
        ttk.Label(filter_frame, text="Wünsche (AU,Rezept)").grid(row=4, column=0, sticky="w", **pad)
        self.wishes = ttk.Entry(filter_frame, width=30)
        self.wishes.grid(row=4, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache (Slot 1)
        ttk.Label(filter_frame, text="Sprache").grid(row=5, column=0, sticky="w", **pad)
        self.language = ttk.Entry(filter_frame, width=30)
        self.language.grid(row=5, column=1, columnspan=2, sticky="ew", **pad)

        # Diagnose ausschließen (Slot 1)
        ttk.Label(filter_frame, text="Diagnose ausschließen").grid(row=6, column=0, sticky="w", **pad)
        self.diagnosis_exclude = ttk.Entry(filter_frame, width=30)
        self.diagnosis_exclude.grid(row=6, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche ausschließen (Slot 1)
        ttk.Label(filter_frame, text="Wünsche ausschließen").grid(row=7, column=0, sticky="w", **pad)
        self.wishes_exclude = ttk.Entry(filter_frame, width=30)
        self.wishes_exclude.grid(row=7, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache ausschließen (Slot 1)
        ttk.Label(filter_frame, text="Sprache ausschließen").grid(row=8, column=0, sticky="w", **pad)
        self.language_exclude = ttk.Entry(filter_frame, width=30)
        self.language_exclude.grid(row=8, column=1, columnspan=2, sticky="ew", **pad)

        # Alter + Geschlecht (Slot 1)
        ttk.Label(filter_frame, text="Alter min").grid(row=9, column=0, sticky="w", **pad)
        self.age_min = ttk.Entry(filter_frame, width=10)
        self.age_min.grid(row=9, column=1, sticky="w", **pad)
        ttk.Label(filter_frame, text="max").grid(row=9, column=2, sticky="w", **pad)
        self.age_max = ttk.Entry(filter_frame, width=10)
        self.age_max.grid(row=9, column=3, sticky="w", **pad)

        ttk.Label(filter_frame, text="Geschlecht").grid(row=10, column=0, sticky="w", **pad)
        self.gender = ttk.Combobox(filter_frame, values=["egal", "männlich", "weiblich", "divers"], state="readonly", width=15)
        self.gender.set("egal")
        self.gender.grid(row=10, column=1, sticky="w", **pad)

        # Max Patienten + Behandlungsintervall (Slot 1)
        ttk.Label(filter_frame, text="Max Patienten").grid(row=11, column=0, sticky="w", **pad)
        self.max_patients = ttk.Spinbox(filter_frame, from_=1, to=100, width=10)
        self.max_patients.set(5)
        self.max_patients.grid(row=11, column=1, sticky="w", **pad)
        ttk.Label(filter_frame, text="Behandlungsintervall (Min)").grid(row=11, column=2, sticky="w", **pad)
        self.interval_minutes = ttk.Spinbox(filter_frame, from_=1, to=60, width=10)
        self.interval_minutes.set(5)
        self.interval_minutes.grid(row=11, column=3, sticky="w", **pad)

        # ===== CHECKBOX: 2. ZEITSLOT AKTIVIEREN =====
        self.slot2_enabled = tk.BooleanVar(value=False)
        slot2_checkbox = ttk.Checkbutton(filter_frame, text="✓ 2. Zeitslot aktivieren",
                                         variable=self.slot2_enabled,
                                         command=self.toggle_slot2)
        slot2_checkbox.grid(row=12, column=0, columnspan=4, sticky="w", **pad)

        # ===== SLOT 2 — wird mit grid_remove() versteckt =====
        self.slot2_frame = ttk.LabelFrame(filter_frame, text="🕑 SLOT 2", padding="5")
        self.slot2_frame.grid(row=13, column=0, columnspan=4, sticky="ew", padx=10, pady=5)
        self.slot2_frame.columnconfigure(1, weight=1)

        # Zeit Slot 2
        ttk.Label(self.slot2_frame, text="Zeit von").grid(row=0, column=0, sticky="w", **pad)
        self.time_from_2 = ttk.Entry(self.slot2_frame, width=10)
        self.time_from_2.insert(0, "14:00")
        self.time_from_2.grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(self.slot2_frame, text="bis").grid(row=0, column=2, sticky="w", **pad)
        self.time_to_2 = ttk.Entry(self.slot2_frame, width=10)
        self.time_to_2.insert(0, "18:00")
        self.time_to_2.grid(row=0, column=3, sticky="w", **pad)

        # Diagnose (Slot 2)
        ttk.Label(self.slot2_frame, text="Diagnose").grid(row=1, column=0, sticky="w", **pad)
        self.diagnosis_2 = ttk.Entry(self.slot2_frame, width=30)
        self.diagnosis_2.grid(row=1, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche (Slot 2)
        ttk.Label(self.slot2_frame, text="Wünsche").grid(row=2, column=0, sticky="w", **pad)
        self.wishes_2 = ttk.Entry(self.slot2_frame, width=30)
        self.wishes_2.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache (Slot 2)
        ttk.Label(self.slot2_frame, text="Sprache").grid(row=3, column=0, sticky="w", **pad)
        self.language_2 = ttk.Entry(self.slot2_frame, width=30)
        self.language_2.grid(row=3, column=1, columnspan=2, sticky="ew", **pad)

        # Diagnose ausschließen (Slot 2)
        ttk.Label(self.slot2_frame, text="Diagnose ausschließen").grid(row=4, column=0, sticky="w", **pad)
        self.diagnosis_exclude_2 = ttk.Entry(self.slot2_frame, width=30)
        self.diagnosis_exclude_2.grid(row=4, column=1, columnspan=2, sticky="ew", **pad)

        # Wünsche ausschließen (Slot 2)
        ttk.Label(self.slot2_frame, text="Wünsche ausschließen").grid(row=5, column=0, sticky="w", **pad)
        self.wishes_exclude_2 = ttk.Entry(self.slot2_frame, width=30)
        self.wishes_exclude_2.grid(row=5, column=1, columnspan=2, sticky="ew", **pad)

        # Sprache ausschließen (Slot 2)
        ttk.Label(self.slot2_frame, text="Sprache ausschließen").grid(row=6, column=0, sticky="w", **pad)
        self.language_exclude_2 = ttk.Entry(self.slot2_frame, width=30)
        self.language_exclude_2.grid(row=6, column=1, columnspan=2, sticky="ew", **pad)

        # Alter + Geschlecht (Slot 2)
        ttk.Label(self.slot2_frame, text="Alter min").grid(row=7, column=0, sticky="w", **pad)
        self.age_min_2 = ttk.Entry(self.slot2_frame, width=10)
        self.age_min_2.grid(row=7, column=1, sticky="w", **pad)
        ttk.Label(self.slot2_frame, text="max").grid(row=7, column=2, sticky="w", **pad)
        self.age_max_2 = ttk.Entry(self.slot2_frame, width=10)
        self.age_max_2.grid(row=7, column=3, sticky="w", **pad)

        ttk.Label(self.slot2_frame, text="Geschlecht").grid(row=8, column=0, sticky="w", **pad)
        self.gender_2 = ttk.Combobox(self.slot2_frame, values=["egal", "männlich", "weiblich", "divers"], state="readonly", width=15)
        self.gender_2.set("egal")
        self.gender_2.grid(row=8, column=1, sticky="w", **pad)

        # Max Patienten + Behandlungsintervall (Slot 2)
        ttk.Label(self.slot2_frame, text="Max Patienten").grid(row=9, column=0, sticky="w", **pad)
        self.max_patients_2 = ttk.Spinbox(self.slot2_frame, from_=1, to=100, width=10)
        self.max_patients_2.set(5)
        self.max_patients_2.grid(row=9, column=1, sticky="w", **pad)
        ttk.Label(self.slot2_frame, text="Behandlungsintervall (Min)").grid(row=9, column=2, sticky="w", **pad)
        self.interval_minutes_2 = ttk.Spinbox(self.slot2_frame, from_=1, to=60, width=10)
        self.interval_minutes_2.set(5)
        self.interval_minutes_2.grid(row=9, column=3, sticky="w", **pad)

        # Verstecke Slot 2 anfangs
        self.slot2_frame.grid_remove()

        # ===== ALLGEMEINE EINSTELLUNGEN =====
        general_label = ttk.Label(filter_frame, text="⚙️ ALLGEMEINE EINSTELLUNGEN", font=("Arial", 10, "bold"))
        general_label.grid(row=14, column=0, columnspan=4, sticky="w", **pad)

        ttk.Label(filter_frame, text="Scan-Intervall (Sek)").grid(row=15, column=0, sticky="w", **pad)
        self.scan_interval = ttk.Spinbox(filter_frame, from_=1, to=30, width=10)
        self.scan_interval.set(8)
        self.scan_interval.grid(row=15, column=1, sticky="w", **pad)

        ttk.Label(filter_frame, text="Max Seiten").grid(row=15, column=2, sticky="w", **pad)
        self.max_pages = ttk.Spinbox(filter_frame, from_=1, to=20, width=10)
        self.max_pages.set(5)
        self.max_pages.grid(row=15, column=3, sticky="w", **pad)

        # --- BUTTONS — IMMER SICHTBAR (außerhalb des Scroll-Bereichs) ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)

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

        self.log_text = scrolledtext.ScrolledText(log_frame, height=5, width=80,
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

    def _on_frame_configure(self, event=None):
        """Aktualisiert die Scroll-Region wenn sich der innere Frame ändert."""
        self.filter_canvas.configure(scrollregion=self.filter_canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        """Passt die Breite des inneren Frames an den Canvas an."""
        self.filter_canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Scrollt den Filter-Canvas mit dem Mausrad."""
        self.filter_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_filters(self):
        """Lade gespeicherte Filter und migriere bei Bedarf zu neuem Format"""
        if FILTER_PATH.exists():
            try:
                with open(FILTER_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Migriere alte zu neuer Format
                    data = migrate_filters_to_slot_format(data)

                    # ===== SLOT 1 =====
                    self.day_window.set(data.get("time_filter", {}).get("day_window", "heute"))
                    slot1 = data.get("slot1", {})

                    self.time_from.delete(0, tk.END)
                    self.time_from.insert(0, slot1.get("time_start", "21:30"))
                    self.time_to.delete(0, tk.END)
                    self.time_to.insert(0, slot1.get("time_end", "23:30"))

                    self.diagnosis.delete(0, tk.END)
                    self.diagnosis.insert(0, slot1.get("diagnosis_include", ""))
                    self.diagnosis_exclude.delete(0, tk.END)
                    self.diagnosis_exclude.insert(0, slot1.get("diagnosis_exclude", ""))

                    self.wishes.delete(0, tk.END)
                    self.wishes.insert(0, slot1.get("wishes_include", ""))
                    self.wishes_exclude.delete(0, tk.END)
                    self.wishes_exclude.insert(0, slot1.get("wishes_exclude", ""))

                    self.language.delete(0, tk.END)
                    self.language.insert(0, slot1.get("language_include", ""))
                    self.language_exclude.delete(0, tk.END)
                    self.language_exclude.insert(0, slot1.get("language_exclude", ""))

                    self.age_min.delete(0, tk.END)
                    self.age_min.insert(0, str(slot1.get("age_min", "")))
                    self.age_max.delete(0, tk.END)
                    self.age_max.insert(0, str(slot1.get("age_max", "")))
                    self.gender.set(slot1.get("gender", "egal"))

                    self.max_patients.set(slot1.get("max_patients", 5))
                    self.interval_minutes.set(slot1.get("interval_minutes", data.get("runtime", {}).get("interval_minutes", 5)))

                    # ===== SLOT 2 =====
                    slot2_enabled = data.get("slot2_enabled", False)
                    self.slot2_enabled.set(slot2_enabled)
                    slot2 = data.get("slot2", {})

                    self.time_from_2.delete(0, tk.END)
                    self.time_from_2.insert(0, slot2.get("time_start", "14:00"))
                    self.time_to_2.delete(0, tk.END)
                    self.time_to_2.insert(0, slot2.get("time_end", "18:00"))

                    self.diagnosis_2.delete(0, tk.END)
                    self.diagnosis_2.insert(0, slot2.get("diagnosis_include", ""))
                    self.diagnosis_exclude_2.delete(0, tk.END)
                    self.diagnosis_exclude_2.insert(0, slot2.get("diagnosis_exclude", ""))

                    self.wishes_2.delete(0, tk.END)
                    self.wishes_2.insert(0, slot2.get("wishes_include", ""))
                    self.wishes_exclude_2.delete(0, tk.END)
                    self.wishes_exclude_2.insert(0, slot2.get("wishes_exclude", ""))

                    self.language_2.delete(0, tk.END)
                    self.language_2.insert(0, slot2.get("language_include", ""))
                    self.language_exclude_2.delete(0, tk.END)
                    self.language_exclude_2.insert(0, slot2.get("language_exclude", ""))

                    self.age_min_2.delete(0, tk.END)
                    self.age_min_2.insert(0, str(slot2.get("age_min", "")))
                    self.age_max_2.delete(0, tk.END)
                    self.age_max_2.insert(0, str(slot2.get("age_max", "")))
                    self.gender_2.set(slot2.get("gender", "egal"))

                    self.max_patients_2.set(slot2.get("max_patients", 5))
                    self.interval_minutes_2.set(slot2.get("interval_minutes", 5))

                    # ===== LOOP SETTINGS =====
                    self.scan_interval.set(data.get("loop", {}).get("scan_interval_sec", 8))
                    self.max_pages.set(data.get("loop", {}).get("max_pages", 5))

                    # Zeige/verstecke Slot 2 basierend auf Flag
                    self.toggle_slot2()
            except Exception as e:
                self.log("⚠️ Fehler beim Laden der Filter: " + str(e))

    def toggle_slot2(self):
        """Zeige/verstecke Slot-2-Block basierend auf Checkbox"""
        if self.slot2_enabled.get():
            self.slot2_frame.grid()
        else:
            self.slot2_frame.grid_remove()

    @staticmethod
    def normalize_time_input(t: str) -> str:
        """Normalisiert Zeiteingabe: ersetzt Punkt durch Doppelpunkt (23.30 → 23:30)."""
        return t.strip().replace(".", ":")

    @staticmethod
    def _safe_int(value, default=0):
        """Konvertiert sicher zu int, gibt default zurück bei leerem/ungültigem Wert."""
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return default

    def save_filters(self):
        """Speichere Filter in neuem Slot-Format"""
        si = self._safe_int
        nt = self.normalize_time_input

        data = {
            "time_filter": {
                "day_window": self.day_window.get()
            },
            "slot1": {
                "time_start": nt(self.time_from.get()),
                "time_end": nt(self.time_to.get()),
                "max_patients": si(self.max_patients.get(), 0),
                "interval_minutes": si(self.interval_minutes.get(), 5),
                "diagnosis_include": self.diagnosis.get().strip(),
                "diagnosis_exclude": self.diagnosis_exclude.get().strip(),
                "wishes_include": self.wishes.get().strip(),
                "wishes_exclude": self.wishes_exclude.get().strip(),
                "language_include": self.language.get().strip(),
                "language_exclude": self.language_exclude.get().strip(),
                "age_min": self.age_min.get().strip(),
                "age_max": self.age_max.get().strip(),
                "gender": self.gender.get() if self.gender.get() != "egal" else ""
            },
            "slot2_enabled": self.slot2_enabled.get(),
            "slot2": {
                "time_start": nt(self.time_from_2.get().strip()),
                "time_end": nt(self.time_to_2.get().strip()),
                "max_patients": si(self.max_patients_2.get(), 0),
                "interval_minutes": si(self.interval_minutes_2.get(), 5),
                "diagnosis_include": self.diagnosis_2.get().strip(),
                "diagnosis_exclude": self.diagnosis_exclude_2.get().strip(),
                "wishes_include": self.wishes_2.get().strip(),
                "wishes_exclude": self.wishes_exclude_2.get().strip(),
                "language_include": self.language_2.get().strip(),
                "language_exclude": self.language_exclude_2.get().strip(),
                "age_min": self.age_min_2.get().strip(),
                "age_max": self.age_max_2.get().strip(),
                "gender": self.gender_2.get() if self.gender_2.get() != "egal" else ""
            },
            "runtime": {
                "interval_minutes": si(self.interval_minutes.get(), 5),
                "headless": False,
                "slowmo_ms": 0
            },
            "patients": {
                "gender": "",
                "age_min": "",
                "age_max": "",
                "language_include": [],
                "language_exclude": []
            },
            "diagnosis": {
                "include": "",
                "exclude": ""
            },
            "wishes": {
                "include": "",
                "exclude": ""
            },
            "loop": {
                "scan_interval_sec": si(self.scan_interval.get(), 5),
                "max_pages": si(self.max_pages.get(), 5)
            }
        }
        try:
            with open(FILTER_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log("✅ Filter gespeichert (Slot 1 + Slot 2)!")
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

        # Vor neuem Lauf: gespeicherte Patienten für das aktuell gewählte Datum zurücksetzen
        try:
            from scheduled_patients import reset_patients_for_date
            from datetime import datetime, timedelta

            day_window = self.day_window.get()
            if day_window == "morgen":
                target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif day_window == "später":
                target_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            else:
                target_date = datetime.now().strftime("%Y-%m-%d")

            reset_patients_for_date(target_date)

            for item in self.appointment_tree.get_children():
                self.appointment_tree.delete(item)

            self.log(f"🧹 Kalenderdaten für {target_date} zurückgesetzt")
        except Exception as e:
            self.log(f"⚠️ Konnte Kalenderdaten nicht zurücksetzen: {e}")

        # Zeige Filter-Übersicht
        self.log("=" * 80)
        self.log("🚀 STARTE BOT - SCANNER & CLICKER")
        self.log("=" * 80)
        self.log(f"📅 TAG: {self.day_window.get()}")
        self.log(f"🕐 ZEIT: {self.time_from.get()} - {self.time_to.get()}")
        if self.time_from_2.get().strip() and self.time_to_2.get().strip():
            self.log(f"🕑 ZEIT 2: {self.time_from_2.get().strip()} - {self.time_to_2.get().strip()}")
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
                            elif (("[OK]" in line and ("bernommen" in line or "übernommen" in line)) or
                                  ("[OK] Termin" in line and "eingetragen" in line) or
                                  "✅ Fall" in line):
                                terminated_count += 1
                                show_line = True
                                formatted_line = f"[{terminated_count}] ✅ {line}"

                                # Sofortige Terminkalender-Aktualisierung
                                self._update_calendar_from_json()
                                last_calendar_update = time.time()

                            # 3. Wichtige Fehler
                            elif "❌" in line and "Fehler" in line:
                                show_line = True
                                formatted_line = f"⚠️ {line}"

                            # 4. Bot-Status / Shutdown-Hinweise nur anzeigen, NICHT Prozess hart beenden
                            elif "Maximale Patientenanzahl erreicht" in line or "SHUTDOWN" in line or "[STOP]" in line:
                                show_line = True
                                formatted_line = f"🛑 {line}"

                            if show_line:
                                self.log_text.config(state="normal")
                                self.log_text.insert("end", formatted_line + "\n")
                                self.log_text.see("end")
                                self.log_text.config(state="disabled")

                # Regelmäßige Terminkalender-Aktualisierung
                current_time = time.time()
                if current_time - last_calendar_update >= 2.0:
                    self._update_calendar_from_json()
                    last_calendar_update = current_time

                time.sleep(0.5)
            except Exception:
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
        if not check_license_before_start():
            print("[ERROR] Keine gültige Lizenz - Programm wird beendet")
            sys.exit(1)
        print("[INFO] Lizenz OK - Starte GUI")

    root = tk.Tk()
    app = TeleClinicBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
