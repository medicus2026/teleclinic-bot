#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TeleClinic Bot - Lizenz-System mit Hardware-Bindung
Verhindert unbefugte Weitergabe durch PC-Bindung
"""

import hashlib
import subprocess
import uuid
import json
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import os
from pathlib import Path

APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "TeleClinic-Bot"
APP_DIR.mkdir(parents=True, exist_ok=True)
LICENSE_FILE = APP_DIR / "license.key"
ACTIVATION_STATUS_FILE = APP_DIR / "activation_status.txt"


class LicenseManager:
    """Verwaltet Lizenzen mit Hardware-Bindung"""

    def __init__(self):
        self.master_password = "Hanbo2001!"  # Master-Passwort für Aktivierung

    def get_hardware_id(self) -> str:
        """
        Erstellt einzigartige Hardware-ID basierend auf:
        - CPU-ID
        - Motherboard Serial
        - MAC-Adresse
        """
        try:
            # Windows: WMIC für Hardware-IDs
            cpu_id = subprocess.check_output(
                "wmic cpu get processorid",
                shell=True
            ).decode().split('\n')[1].strip()

            motherboard = subprocess.check_output(
                "wmic baseboard get serialnumber",
                shell=True
            ).decode().split('\n')[1].strip()

            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                           for ele in range(0,8*6,8)][::-1])

            # Kombiniere alle IDs
            combined = "{}-{}-{}".format(cpu_id, motherboard, mac)

            # Hash für Privatsphäre
            hw_id = hashlib.sha256(combined.encode()).hexdigest()[:16]
            return hw_id

        except Exception as e:
            print("Fehler beim Erstellen der Hardware-ID: {}".format(e))
            # Fallback: Nur MAC-Adresse
            mac = uuid.getnode()
            return hashlib.sha256(str(mac).encode()).hexdigest()[:16]

    def generate_license_key(self, hardware_id: str, days_valid: int = 365) -> dict:
        """
        Erstellt Lizenzschlüssel für spezifische Hardware

        Format:
        {
            "hardware_id": "abc123...",
            "created": "2026-02-04",
            "expires": "2027-02-04",
            "activated_by": "GIZ Praxis",
            "signature": "xyz..."
        }
        """
        created = datetime.now()
        expires = created + timedelta(days=days_valid)

        license_data = {
            "hardware_id": hardware_id,
            "created": created.strftime("%Y-%m-%d %H:%M:%S"),
            "expires": expires.strftime("%Y-%m-%d %H:%M:%S"),
            "activated_by": "GIZ Praxis",
            "version": "2.0.0"
        }

        # Signatur erstellen (verhindert Manipulation)
        signature_base = "{}{}{}{}".format(hardware_id, created, expires, self.master_password)
        license_data["signature"] = hashlib.sha256(signature_base.encode()).hexdigest()

        return license_data

    def save_license(self, license_data: dict):
        """Speichere Lizenz auf PC"""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(LICENSE_FILE, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2)
        ACTIVATION_STATUS_FILE.write_text('activated', encoding='utf-8')

    def load_license(self):  # Rückgabetyp: dict oder None
        """Lade gespeicherte Lizenz"""
        if not LICENSE_FILE.exists():
            return None

        try:
            with open(LICENSE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def verify_license(self) -> tuple[bool, str]:
        """
        Prüft ob Lizenz gültig ist

        Returns:
            (is_valid, error_message)
        """
        license_data = self.load_license()

        # 1. Lizenz vorhanden?
        if not license_data:
            if ACTIVATION_STATUS_FILE.exists():
                return False, "Aktivierungsstatus gefunden, aber Lizenzdatei fehlt oder ist beschädigt. Bitte erneut aktivieren."
            return False, "Keine Lizenz gefunden! Bitte aktivieren Sie das Programm."

        # 2. Hardware-ID prüfen
        current_hw_id = self.get_hardware_id()
        if license_data.get("hardware_id") != current_hw_id:
            return False, ("FEHLER: Lizenz ist für einen anderen PC!\n\n"
                          "Diese Software ist an einen bestimmten PC gebunden.\n"
                          "Kontaktieren Sie den Administrator für eine neue Lizenz.")

        # 3. Signatur prüfen (Manipulation?)
        signature_base = "{}{}{}{}".format(license_data['hardware_id'], license_data['created'], license_data['expires'], self.master_password)
        expected_sig = hashlib.sha256(signature_base.encode()).hexdigest()

        if license_data.get("signature") != expected_sig:
            return False, "FEHLER: Lizenz wurde manipuliert!"

        # 4. Ablaufdatum prüfen
        try:
            expires = datetime.strptime(license_data['expires'], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expires:
                return False, "Lizenz abgelaufen am {}".format(license_data['expires'])
        except Exception:
            return False, "Fehler beim Prüfen des Ablaufdatums"

        return True, "Lizenz gültig"

    def activate(self, activation_password: str) -> tuple[bool, str]:
        """
        Aktiviert Software auf diesem PC

        Args:
            activation_password: Master-Passwort

        Returns:
            (success, message)
        """
        # Prüfe Passwort
        if activation_password != self.master_password:
            return False, "Falsches Aktivierungs-Passwort!"

        # Erstelle Hardware-ID
        hw_id = self.get_hardware_id()

        # Generiere Lizenz (365 Tage)
        license_data = self.generate_license_key(hw_id, days_valid=365)

        # Speichere Lizenz
        self.save_license(license_data)

        expires = license_data['expires']
        return True, "✅ Aktivierung erfolgreich!\n\nGültig bis: {}\nHardware-ID: {}".format(expires, hw_id)


class ActivationDialog:
    """GUI-Dialog für Software-Aktivierung"""

    def __init__(self):
        self.license_mgr = LicenseManager()
        self.result = None

    def show(self) -> bool:
        """
        Zeigt Aktivierungs-Dialog

        Returns:
            True wenn erfolgreich aktiviert, sonst False
        """
        root = tk.Tk()
        root.title("TeleClinic AutoBot - Aktivierung erforderlich")
        root.geometry("500x350")
        root.resizable(False, False)

        # Zentriere Fenster
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (500 // 2)
        y = (root.winfo_screenheight() // 2) - (350 // 2)
        root.geometry("500x350+{}+{}".format(x, y))

        # Header
        header = tk.Label(
            root,
            text="🔐 Software-Aktivierung erforderlich",
            font=("Arial", 14, "bold"),
            fg="#1a5490"
        )
        header.pack(pady=20)

        # Info-Text
        hw_id = self.license_mgr.get_hardware_id()
        info_text = (
            "Diese Software ist lizenzgeschützt und an einen\n"
            "bestimmten PC gebunden.\n\n"
            "Bitte geben Sie das Aktivierungs-Passwort ein,\n"
            "um die Software auf diesem PC zu aktivieren.\n\n"
            "Hardware-ID dieses PCs:\n{}".format(hw_id)
        )

        info = tk.Label(root, text=info_text, justify="left", font=("Arial", 9))
        info.pack(pady=10)

        # Passwort-Eingabe
        pw_frame = tk.Frame(root)
        pw_frame.pack(pady=20)

        tk.Label(pw_frame, text="Aktivierungs-Passwort:", font=("Arial", 10)).pack()

        password_var = tk.StringVar()
        password_entry = tk.Entry(pw_frame, textvariable=password_var, show="*",
                                 width=30, font=("Arial", 11))
        password_entry.pack(pady=5)
        password_entry.focus()

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)

        def activate():
            password = password_var.get()
            if not password:
                messagebox.showerror("Fehler", "Bitte geben Sie das Passwort ein!")
                return

            success, message = self.license_mgr.activate(password)

            if success:
                messagebox.showinfo("Erfolg", message)
                self.result = True
                root.quit()
                root.destroy()
            else:
                messagebox.showerror("Fehler", message)
                password_entry.delete(0, tk.END)
                password_entry.focus()

        def cancel():
            self.result = False
            root.quit()
            root.destroy()

        # Enter-Taste für Aktivierung
        password_entry.bind('<Return>', lambda e: activate())

        tk.Button(
            btn_frame,
            text="✅ Aktivieren",
            command=activate,
            bg="#2ecc71",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="❌ Abbrechen",
            command=cancel,
            bg="#e74c3c",
            fg="white",
            font=("Arial", 10, "bold"),
            width=15,
            height=2
        ).pack(side="left", padx=5)

        # Hinweis
        hint = tk.Label(
            root,
            text="Hinweis: Kontaktieren Sie Ihren Administrator\nfür das Aktivierungs-Passwort.",
            font=("Arial", 8),
            fg="gray"
        )
        hint.pack(pady=10)

        # Hinweis: Überspringe Aktivierung, wenn bereits aktiviert
        if ACTIVATION_STATUS_FILE.exists():
            if ACTIVATION_STATUS_FILE.read_text(encoding='utf-8').strip() == 'activated':
                messagebox.showinfo("Info", "Software ist bereits aktiviert.")
                self.result = True
                root.quit()
                root.destroy()
                return self.result

        root.protocol("WM_DELETE_WINDOW", cancel)
        root.mainloop()

        return self.result if self.result is not None else False


def check_license_before_start() -> bool:
    """
    Prüft Lizenz vor Programmstart

    Returns:
        True wenn Lizenz OK, False sonst
    """
    license_mgr = LicenseManager()

    # Prüfe bestehende Lizenz
    is_valid, message = license_mgr.verify_license()

    if is_valid:
        print("✅ Lizenz gültig")
        return True

    # Lizenz ungültig oder nicht vorhanden → Aktivierungs-Dialog
    print("⚠️ {}".format(message))
    print("Zeige Aktivierungs-Dialog...")

    dialog = ActivationDialog()
    activated = dialog.show()

    if not activated:
        messagebox.showerror(
            "Keine Lizenz",
            "Das Programm kann ohne gültige Lizenz nicht gestartet werden.\n\n"
            "Kontaktieren Sie Ihren Administrator."
        )
        return False

    return True


# Admin-Tool: Zeige Hardware-ID
def show_hardware_id():
    """Zeigt Hardware-ID für Admin"""
    license_mgr = LicenseManager()
    hw_id = license_mgr.get_hardware_id()

    print("="*60)
    print("  HARDWARE-ID (für Lizenz-Erstellung)")
    print("="*60)
    print("\n  {}\n".format(hw_id))
    print("="*60)

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        "Hardware-ID",
        "Hardware-ID dieses PCs:\n\n{}\n\n"
        "Diese ID wird für die Lizenz-Aktivierung benötigt.".format(hw_id)
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--show-id":
        # Admin-Modus: Zeige Hardware-ID
        show_hardware_id()
    else:
        # Test: Lizenz prüfen/aktivieren
        if check_license_before_start():
            print("✅ Lizenz OK - Programm kann starten")
        else:
            print("❌ Keine gültige Lizenz - Programm beendet")
