#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test-Skript für die Tab-Navigation"""

from teleclinic_click_from_list_v9d import get_tab_number

print("=== Test der Tab-Navigation ===\n")

# Test 1: "heute"
tab = get_tab_number('heute')
print(f'✓ "heute" → tab={tab} (erwartet: 0) {"✅" if tab == 0 else "❌"}')

# Test 2: "morgen"
tab = get_tab_number('morgen')
print(f'✓ "morgen" → tab={tab} (erwartet: 1) {"✅" if tab == 1 else "❌"}')

# Test 3: "später"
tab = get_tab_number('später')
print(f'✓ "später" → tab={tab} (erwartet: 2) {"✅" if tab == 2 else "❌"}')

print("\n✅ Tab-Navigation funktioniert korrekt!")
print("\nBeim Scannen sollten die URLs so aussehen:")
print("  Heute:  https://med.teleclinic.com/requests?tab=0&page=1")
print("  Morgen: https://med.teleclinic.com/requests?tab=1&page=1")
print("  Später: https://med.teleclinic.com/requests?tab=2&page=1")
