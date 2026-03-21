#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test der Scheduler-Validierung mit unmöglichem Wunsch"""

from core_scheduler import validate_max_patients
import json

# Modifiziere Filter: max_patients zu 100
filters = json.load(open('filters.json'))
filters['runtime']['max_patients'] = 100

print("\nTest mit max_patients = 100 (unmöglich):")
print("-" * 70)
requested, possible, valid = validate_max_patients(filters)
print(f"Ergebnis: Requested={requested}, Possible={possible}, Valid={valid}\n")
