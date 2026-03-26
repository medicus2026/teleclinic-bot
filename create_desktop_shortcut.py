"""
Erstellt eine Desktop-Verknüpfung für den TeleClinic Bot.
Einmalig ausführen: python create_desktop_shortcut.py
"""
import os
import sys
from pathlib import Path

def create_shortcut():
    # Desktop-Pfad ermitteln
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    if not desktop.exists():
        # Fallback für OneDrive-Desktop
        desktop = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Desktop"

    lnk_path = desktop / "TeleClinic Bot.lnk"
    bat_path = Path("C:/teleclinic-bot/start_teleclinic_bot.bat")
    work_dir = Path("C:/teleclinic-bot")
    ico_path = Path("C:/teleclinic-bot/Logo_Teleclinic_scanner.ico")

    # Icon: eigenes ICO wenn vorhanden und nicht leer, sonst Windows-Standard
    if ico_path.exists() and ico_path.stat().st_size > 0:
        icon = str(ico_path)
    else:
        icon = "C:\\Windows\\System32\\shell32.dll,167"

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(lnk_path))
        shortcut.Targetpath = str(bat_path)
        shortcut.WorkingDirectory = str(work_dir)
        shortcut.WindowStyle = 1
        shortcut.Description = "TeleClinic AutoBot starten"
        shortcut.IconLocation = icon
        shortcut.save()
        print(f"✅ Verknüpfung erstellt: {lnk_path}")
        return True
    except ImportError:
        # win32com nicht verfügbar → VBScript-Fallback
        vbs = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{lnk_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{bat_path}"
oLink.WorkingDirectory = "{work_dir}"
oLink.WindowStyle = 1
oLink.Description = "TeleClinic AutoBot starten"
oLink.IconLocation = "{icon}"
oLink.Save
"""
        vbs_path = Path("C:/teleclinic-bot/_tmp_shortcut.vbs")
        vbs_path.write_text(vbs, encoding="utf-8")
        ret = os.system(f'cscript //nologo "{vbs_path}"')
        vbs_path.unlink(missing_ok=True)
        if ret == 0 and lnk_path.exists():
            print(f"✅ Verknüpfung erstellt (VBS): {lnk_path}")
            return True
        else:
            print(f"❌ Fehler beim Erstellen der Verknüpfung (VBS, Code {ret})")
            return False

if __name__ == "__main__":
    ok = create_shortcut()
    sys.exit(0 if ok else 1)
