#!/usr/bin/env python3
import re

text = "Heute, 22:00 - Morgen, 00:00"
text_cleaned = re.sub(r'(Heute|Today|Morgen|Tomorrow|Später|Later|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mo|Di|Mi|Do|Fr|Sa|So|[A-Z][a-z]+day),?\s*', '', text, flags=re.IGNORECASE)
print(f"Original: '{text}'")
print(f"Bereinigt: '{text_cleaned}'")

match = re.search(r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', text_cleaned)
if match:
    print(f"Match gefunden: {match.groups()}")
else:
    print("Kein Match!")
