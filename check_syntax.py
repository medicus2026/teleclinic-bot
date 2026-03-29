import ast, sys
files = [
    "teleclinic_click_from_list_v9d.py",
    "tc_main_gui.py",
    "import_appointments_helper.py",
    "scheduled_patients.py",
    "core_scheduler.py",
]
all_ok = True
for f in files:
    try:
        src = open(f, "r", encoding="utf-8").read()
        ast.parse(src)
        print(f"OK: {f}")
    except SyntaxError as e:
        print(f"FEHLER in {f}: {e}")
        all_ok = False
    except FileNotFoundError:
        print(f"NICHT GEFUNDEN: {f}")

if all_ok:
    print("\nAlle Dateien: Syntax OK")
else:
    print("\nSyntax-Fehler gefunden!")
    sys.exit(1)
