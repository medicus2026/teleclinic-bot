#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test des Schedulers mit File-Locking"""

from core_scheduler import next_available_slot
import json

filters = json.load(open('filters.json'))

print("\n" + "="*70)
print("TEST: Scheduler mit File-Locking")
print("="*70)

# Lösche alte Slots
import json
with open('scheduled_slots.json', 'w') as f:
    json.dump({}, f)

print("\n3 aufeinanderfolgende Aufrufe:")
print("1:", next_available_slot(filters))
print("2:", next_available_slot(filters))
print("3:", next_available_slot(filters))

print("\n" + "="*70)
print("scheduled_slots.json Inhalt:")
with open('scheduled_slots.json', 'r') as f:
    print(f.read())
print("="*70)
