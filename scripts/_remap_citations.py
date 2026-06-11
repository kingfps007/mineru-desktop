#!/usr/bin/env python3
"""Map old citation keys to Zotero exported keys based on title matching."""
import re, sys

# Read old references.bib
with open('references.bib', 'r', encoding='utf-8') as f:
    old_text = f.read()

# Read Zotero exported bib
with open('导出的条目.bib', 'r', encoding='utf-8') as f:
    zotero_text = f.read()

# Extract entries from old bib: key -> title
old_entries = {}
for m in re.finditer(r'@\w+\{(\w+),\s*\n  title = \{(.+?)\},', old_text, re.DOTALL):
    key = m.group(1)
    title = re.sub(r'\s+', ' ', m.group(2).replace('{','').replace('}','').lower().strip())[:80]
    old_entries[key] = title

# Extract entries from Zotero bib: key -> title  
zotero_entries = {}
for m in re.finditer(r'@\w+\{(\w+),\s*\n  title = \{(.+?)\},', zotero_text, re.DOTALL):
    key = m.group(1)
    title = re.sub(r'\s+', ' ', m.group(2).replace('{','').replace('}','').lower().strip())[:80]
    zotero_entries[key] = title

print(f"Old keys: {len(old_entries)}, Zotero keys: {len(zotero_entries)}")

# Build mapping: old_key -> zotero_key
key_map = {}
for old_key, old_title in old_entries.items():
    best = None
    best_score = 0
    for zot_key, zot_title in zotero_entries.items():
        # Simple common word matching
        old_words = set(old_title.split())
        zot_words = set(zot_title.split())
        common = len(old_words & zot_words)
        if common > best_score and common >= 2:
            best = zot_key
            best_score = common
    if best:
        key_map[old_key] = best
        print(f"  {old_key:30s} -> {best}")
    else:
        print(f"  {old_key:30s} -> NO MATCH!")

print(f"\nMapped: {len(key_map)}/{len(old_entries)}")

# Read Final_Review.md
with open('Final_Review.md', 'r', encoding='utf-8') as f:
    md_text = f.read()

# Replace [@old_key] with [@zotero_key]
count = 0
for old_key, zot_key in key_map.items():
    pattern = f'[@\\s*{re.escape(old_key)}\\b'
    # Find all [@old_key] patterns (possibly with spaces/semicolons)
    for m in re.finditer(r'\[@' + re.escape(old_key) + r'([\];\s]|$)', md_text):
        pass  # just checking

# Simpler approach: direct string replacement
for old_key, zot_key in key_map.items():
    old_str = f'@{old_key}'
    new_str = f'@{zot_key}'
    if old_str in md_text:
        n = md_text.count(old_str)
        md_text = md_text.replace(old_str, new_str)
        count += n

print(f"\nTotal replacements in MD: {count}")

# Write updated MD
with open('Final_Review.md', 'w', encoding='utf-8') as f:
    f.write(md_text)

# Copy Zotero bib as references.bib
import shutil
shutil.copy('references.bib', 'references_old.bib')
shutil.copy('导出的条目.bib', 'references.bib')
print("\nCopied 导出的条目.bib -> references.bib (backup: references_old.bib)")
print("Done!")
