import os

files = [
    'tc_main_gui.py',
    'teleclinic_click_from_list_v9d.py',
    'core_scheduler.py',
    'scheduled_patients.py',
    'scheduled_patients.json',
    'scheduled_slots.json',
    'import_appointments_helper.py',
    'test_import_standalone.py',
    'license_system.py',
]

src = r'C:\teleclinic-bot'
for f in files:
    fp = os.path.join(src, f)
    exists = os.path.exists(fp)
    size = os.path.getsize(fp) if exists else -1
    print(repr(fp) + ' -> exists=' + str(exists) + ' size=' + str(size))
