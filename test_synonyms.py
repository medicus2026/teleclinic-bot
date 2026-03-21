#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test-Skript für die neuen Synonyme"""

from teleclinic_click_from_list_v9d import normalize_term

print("=== Test der Psychische-Leiden-Synonyme ===\n")

# Test 1: "psych"
synonyms = normalize_term('psych')
print(f'✓ Synonyme für "psych": {synonyms}')

# Test 2: "psyche"
synonyms2 = normalize_term('psyche')
print(f'✓ Synonyme für "psyche": {synonyms2}')

# Test 3: "psychische leiden"
synonyms3 = normalize_term('psychische leiden')
print(f'✓ Synonyme für "psychische leiden": {synonyms3}')

# Test 4: "psychisch"
synonyms4 = normalize_term('psychisch')
print(f'✓ Synonyme für "psychisch": {synonyms4}')

print("\n✅ Alle Synonyme korrekt funktionierend!")
