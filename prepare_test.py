#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test-Vorbereitung und Anzeige der Filter"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from core_scheduler import reset_slots_for_date

# Reset die scheduled_slots.json für morgen
tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
reset_slots_for_date(tomorrow)
print(f'✅ Scheduler-Slots für {tomorrow} zurückgesetzt\n')

# Zeige Filter
filters_path = Path('filters.json')
filters = json.loads(filters_path.read_text(encoding='utf-8'))

print('📋 Aktuelle Filter:')
print(f'  Tag: {filters["time_filter"]["day_window"]}')
print(f'  Zeit: {filters["time_filter"]["treatment_start"]} - {filters["time_filter"]["treatment_end"]}')
print(f'  Diagnose: {filters["diagnosis"]["include"]}')
print(f'  Max Patienten: {filters["runtime"]["max_patients"]}')
print(f'  Intervall: {filters["runtime"]["interval_minutes"]} Minuten')
print(f'\n✅ Vorbereitung abgeschlossen! Scanner kann gestartet werden.')
