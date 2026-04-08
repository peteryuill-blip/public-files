#!/usr/bin/env python3
"""NEON DATAWEB PIPELINE v1.0
Project 666 / Neon — Living Sovereign Dataweb V2 Generator

Place this script in the same folder as all input files and run:
    python3 neon_dataweb_pipeline.py

Requirements: Python 3.8+, stdlib only.
"""

import json
import csv
import re
import os
import sys
import random
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

INPUT_DATAWEB    = "99_LIVING_SOVEREIGN_DATAWEB.md"
INPUT_CSO_MASTER = "99_CY_1_150_CSO_MASTER.md"
INPUT_Q1         = "99_Q1_CRUCIBLE_DATAWEB_V8.md"
INPUT_CRUCIBLE   = "99_CRUCIBLE_MASTER_DATABASE.md"
INPUT_CSV        = "COMPLETE_SOVEREIGN_ID_INDEX_V3.csv"
OUTPUT_FILE      = "99_LIVING_SOVEREIGN_DATAWEB_V2.md"

TODAY = datetime.now().strftime("%Y-%m-%d")

CSO_FIELDS = [
    "visual_telemetry",
    "composition",
    "mark_character_and_gestural_vocabulary",
    "ink_behavior_and_material_interaction",
    "tonal_architecture",
    "edge_behavior",
    "spatial_depth_and_void",
    "temporal_reading",
    "singular_observations",
]

SUBSTRATE_NAMES = {
    "S1":  "Japanese Tissue / Shoji",
    "S2":  "Heavy Arches 300gsm HP",
    "S3":  "Fabriano Artistico 640gsm HP",
    "S4":  "Hahnemuhle Bamboo / Natural",
    "S5":  "Sumi-e Practice Paper",
    "S6":  "Fabriano Unica Printmaking",
    "S7":  "BFK Rives 270gsm",
    "S8":  "Arches 140gsm CP",
    "S9":  "Waterford 140gsm HP",
    "S10": "Yupo Synthetic",
    "S11": "Other / Unknown",
}

# Pipeline run tracking (module-level, populated throughout)
PIPELINE_REPORT = {
    "steps_completed": [],
    "cso_upgraded": 0,
    "cso_already_full": 0,
    "cso_stubs": 0,
    "cso_not_found": 0,
    "patches_by_field": {},
    "works_patched": 0,
    "sections_removed": [],
    "id_bridge_count": 0,
    "oracle_fields_added": [],
}

# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────

def strip_markdown_fences(content: str) -> str:
    """Remove opening and closing markdown code fences."""
    content = re.sub(r'^```[a-zA-Z]*\r?\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\s*$', '', content, flags=re.MULTILINE)
    return content.strip()


def safe_float(val, default=None):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def safe_int(val, default=None):
    try:
        return int(str(val).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def is_empty(val) -> bool:
    """True if val is None, empty string, empty list, or empty dict."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == '':
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


def banner(msg: str):
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print('=' * 60)


def step_log(msg: str):
    print(f"  > {msg}")


def read_file(filepath: str) -> str:
    """Read a file with UTF-8 encoding, replacing errors."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


# ─────────────────────────────────────────────────────────────
# STEP 1a: PARSE LIVING SOVEREIGN DATAWEB
# ─────────────────────────────────────────────────────────────

def parse_dataweb(filepath: str) -> dict:
    """Parse the main dataweb JSON file wrapped in markdown fences."""
    print(f"\n  Parsing Living Sovereign Dataweb: {filepath}")
    if not os.path.exists(filepath):
        print(f"  [CRITICAL] File not found: {filepath}")
        sys.exit(1)

    content = read_file(filepath)
    stripped = strip_markdown_fences(content)

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed in {filepath}: {e}")
        print(f"  [DEBUG] First 200 chars: {stripped[:200]}")
        sys.exit(1)

    ca_count = len(data.get('canonical_archive', {}))
    te_count = len(data.get('temporal_engine', {}))
    print(f"  Loaded OK — canonical_archive: {ca_count} entries, temporal_engine: {te_count} weeks")
    return data


# ─────────────────────────────────────────────────────────────
# STEP 1b: PARSE CSV ID BRIDGE
# ─────────────────────────────────────────────────────────────

def parse_csv_id_bridge(filepath: str):
    """
    Parse the ID bridge CSV.
    Columns: Artwork Title | SEC Routing Tag | New Canonical ID (V14) | Hist Ref 1 | Hist Ref 2
    T-codes appear in title as "T_001 (Crucible Year Record)".

    Returns: (t_to_canonical, canonical_to_t, canonical_to_sec, canonical_to_title)
    """
    print(f"\n  Parsing ID Bridge CSV: {filepath}")
    t_to_canonical   = {}
    canonical_to_t   = {}
    canonical_to_sec = {}
    canonical_to_title = {}

    if not os.path.exists(filepath):
        print(f"  [WARNING] File not found: {filepath}")
        return t_to_canonical, canonical_to_t, canonical_to_sec, canonical_to_title

    content = read_file(filepath)
    lines = content.splitlines()
    reader = csv.DictReader(lines)
    headers = reader.fieldnames or []
    print(f"  CSV headers detected: {headers}")

    def find_col(hdrs, *keywords):
        """Find column name matching all keywords (case-insensitive)."""
        for h in hdrs:
            hl = h.lower().strip()
            if all(k in hl for k in keywords):
                return h
        for h in hdrs:
            hl = h.lower().strip()
            if any(k in hl for k in keywords):
                return h
        return None

    title_col     = find_col(headers, 'title') or find_col(headers, 'artwork')
    sec_col       = find_col(headers, 'sec') or find_col(headers, 'routing')
    canonical_col = find_col(headers, 'canonical') or find_col(headers, 'v14') or find_col(headers, 'new')

    # Positional fallbacks
    if not title_col and len(headers) >= 1:     title_col = headers[0]
    if not sec_col and len(headers) >= 2:       sec_col = headers[1]
    if not canonical_col and len(headers) >= 3: canonical_col = headers[2]

    print(f"  Column mapping — title: '{title_col}' | sec: '{sec_col}' | canonical: '{canonical_col}'")

    row_count = 0
    skipped = 0
    for row in reader:
        row = {(k or '').strip(): (v or '').strip() for k, v in row.items() if k}

        title_val     = row.get(title_col, '')
        sec_val       = row.get(sec_col, '')
        canonical_val = row.get(canonical_col, '')

        # Extract T-code
        t_match = re.search(r'(T_\d{3})', title_val)
        if not t_match:
            skipped += 1
            continue

        t_code = t_match.group(1)

        # Clean canonical ID
        canonical_id = re.sub(r'[^0-9a-zA-Z\-]', '', canonical_val).strip()
        if not canonical_id:
            skipped += 1
            continue

        t_to_canonical[t_code]     = canonical_id
        canonical_to_t[canonical_id]   = t_code
        if sec_val:
            canonical_to_sec[canonical_id] = sec_val
        canonical_to_title[canonical_id] = title_val
        row_count += 1

    print(f"  Mapped {row_count} T-codes | skipped {skipped} non-T-code rows")
    return t_to_canonical, canonical_to_t, canonical_to_sec, canonical_to_title


# ─────────────────────────────────────────────────────────────
# STEP 1c: PARSE CSO MASTER (regex-based, not yaml)
# ─────────────────────────────────────────────────────────────

def parse_cso_section_text(section_text: str, t_code: str) -> dict:
    """
    Line-by-line parser for a single CSO section.
    Handles YAML-like field: value blocks where values may span multiple lines.
    """
    entry = {'_t_code': t_code}

    # All fields we recognise (canonical + extras for stub detection)
    all_fields = CSO_FIELDS + ['surface', 'surfaces', 'dimensions', 'medium', 'mediums']

    # Build alias → canonical map for rapid lookup
    alias_to_canonical = {}
    for f in all_fields:
        for alias in [
            f,
            f.replace('_', ' '),
            f.replace('_', '-'),
            f.replace('_', ''),
            f.replace('_', ' ').title(),
        ]:
            alias_to_canonical[alias.lower()] = f

    current_field = None
    current_lines = []

    def flush():
        nonlocal current_field, current_lines
        if current_field:
            val = '\n'.join(current_lines).strip()
            # Strip leading YAML list markers
            val = re.sub(r'(?m)^[-*]\s+', '', val)
            # Strip YAML block scalar indicators from first line
            val = re.sub(r'^[|>][+-]?\s*\n?', '', val).strip()
            if val:
                entry[current_field] = val
        current_field = None
        current_lines = []

    for line in section_text.split('\n'):
        stripped = line.strip()

        # Stop at next markdown section header
        if re.match(r'^#{1,6}\s', stripped) and stripped != '':
            flush()
            break

        # Detect field: value line
        if ':' in stripped:
            colon_idx = stripped.index(':')
            raw_key = stripped[:colon_idx].strip().lower()
            # Normalise spaces/hyphens → underscores
            norm_key = re.sub(r'[\s\-]+', '_', raw_key)

            canonical = alias_to_canonical.get(raw_key) or alias_to_canonical.get(norm_key)
            if canonical:
                flush()
                current_field = canonical
                rest = stripped[colon_idx + 1:].strip()
                current_lines = [rest] if rest else []
                continue

        # Continuation line
        if current_field is not None:
            current_lines.append(line)

    flush()
    return entry


def parse_cso_master(filepath: str) -> dict:
    """
    Parse CSO Master YAML file into per-artwork dicts keyed by T-code.
    Uses regex section splitting — NOT a YAML parser.
    """
    print(f"\n  Parsing CSO Master: {filepath}")
    cso_data = {}

    if not os.path.exists(filepath):
        print(f"  [WARNING] File not found: {filepath}")
        return cso_data

    content = read_file(filepath)

    # Strip markdown fences if present
    if content.strip().startswith('```'):
        content = strip_markdown_fences(content)

    # Find all T-code section headers (## T_001, ### T_001, T_001 — Title, etc.)
    header_pat = re.compile(r'(?m)^(?:#+\s*)?(T_\d{3})\b[^\n]*$')
    matches = list(header_pat.finditer(content))
    print(f"  Found {len(matches)} T-code sections in CSO Master")

    if not matches:
        print(f"  [WARNING] No T-code sections detected. Check file format.")
        return cso_data

    for i, match in enumerate(matches):
        t_code = match.group(1)
        start  = match.end()
        end    = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_text = content[start:end]

        entry = parse_cso_section_text(section_text, t_code)
        entry['_raw_length'] = len(section_text)
        cso_data[t_code] = entry

    full_count = sum(1 for e in cso_data.values() if any(f in e for f in CSO_FIELDS))
    stub_count = len(cso_data) - full_count
    print(f"  CSO sections: {len(cso_data)} total | {full_count} with content | {stub_count} stubs")
    return cso_data


# ─────────────────────────────────────────────────────────────
# STEP 1d: PARSE Q1 CRUCIBLE DATAWEB
# ─────────────────────────────────────────────────────────────

def parse_q1_dataweb(filepath: str) -> dict:
    """
    Parse Q1 Crucible Dataweb (JSON in markdown fences).
    Returns dict keyed by T-code.
    """
    print(f"\n  Parsing Q1 Dataweb: {filepath}")
    if not os.path.exists(filepath):
        print(f"  [WARNING] File not found: {filepath}")
        return {}

    content = read_file(filepath)
    stripped = strip_markdown_fences(content)

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed in {filepath}: {e}")
        print(f"  [DEBUG] First 200 chars: {stripped[:200]}")
        return {}

    # artworks may be under a key or be the root
    artworks_raw = data.get('artworks', data)

    t_pat = re.compile(r'^T_\d{3}$')

    if isinstance(artworks_raw, list):
        result = {}
        for item in artworks_raw:
            if not isinstance(item, dict):
                continue
            t_code = str(
                item.get('t_code') or item.get('code') or
                item.get('id') or item.get('T_code') or ''
            ).strip()
            if t_pat.match(t_code):
                result[t_code] = item
        print(f"  Q1 artworks (list → dict): {len(result)} entries")
        return result

    if isinstance(artworks_raw, dict):
        result = {k: v for k, v in artworks_raw.items() if t_pat.match(str(k))}
        if result:
            print(f"  Q1 artworks (dict): {len(result)} entries")
            return result
        # Maybe artworks is nested differently — search root for T-code keys
        result = {k: v for k, v in data.items() if t_pat.match(str(k))}
        print(f"  Q1 artworks (root T-code keys): {len(result)} entries")
        return result

    print(f"  [WARNING] Unexpected Q1 structure, returning empty")
    return {}


# ─────────────────────────────────────────────────────────────
# STEP 1e: PARSE CRUCIBLE MASTER DATABASE
# ─────────────────────────────────────────────────────────────

def parse_crucible_master(filepath: str) -> dict:
    """
    Parse Crucible Master Database (bare JSON, no fences).
    Returns dict of crucible_trials keyed by T-code.
    """
    print(f"\n  Parsing Crucible Master: {filepath}")
    if not os.path.exists(filepath):
        print(f"  [WARNING] File not found: {filepath}")
        return {}

    content = read_file(filepath)
    t_pat = re.compile(r'^T_\d{3}$')

    # Try raw, then stripped
    for label, text in [("raw", content), ("stripped", strip_markdown_fences(content))]:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue

        trials_raw = data.get('crucible_trials')

        if isinstance(trials_raw, list):
            result = {}
            for item in trials_raw:
                if not isinstance(item, dict):
                    continue
                t_code = str(
                    item.get('t_code') or item.get('code') or item.get('id') or ''
                ).strip()
                if t_pat.match(t_code):
                    result[t_code] = item
            print(f"  Crucible trials (list, {label}): {len(result)} entries")
            return result

        if isinstance(trials_raw, dict):
            result = {k: v for k, v in trials_raw.items() if t_pat.match(str(k))}
            print(f"  Crucible trials (dict, {label}): {len(result)} entries")
            return result

        # No crucible_trials key — look for T-codes at root
        result = {k: v for k, v in data.items() if t_pat.match(str(k))}
        if result:
            print(f"  Crucible data (root T-code keys, {label}): {len(result)} entries")
            return result

        print(f"  [WARNING] No crucible_trials key found in {filepath} ({label})")
        return {}

    print(f"  [ERROR] Could not parse {filepath}")
    print(f"  [DEBUG] First 200 chars: {content[:200]}")
    return {}


# ─────────────────────────────────────────────────────────────
# STEP 2: BUILD ID BRIDGE
# ─────────────────────────────────────────────────────────────

def build_id_bridge(dataweb: dict, t_to_canonical: dict, canonical_to_t: dict,
                    canonical_to_sec: dict, canonical_to_title: dict) -> None:
    """Add id_bridge top-level section to dataweb."""
    dataweb['id_bridge'] = {
        "t_to_canonical":    t_to_canonical,
        "canonical_to_t":    canonical_to_t,
        "canonical_to_sec":  canonical_to_sec,
        "canonical_to_title": canonical_to_title,
        "total_mapped":      len(t_to_canonical),
    }
    PIPELINE_REPORT['id_bridge_count'] = len(t_to_canonical)
    step_log(f"ID bridge: {len(t_to_canonical)} T-code ↔ canonical mappings")
    PIPELINE_REPORT['steps_completed'].append("Step 2: ID Bridge built")


# ─────────────────────────────────────────────────────────────
# STEP 3: MIGRATE CSO REPORTS
# ─────────────────────────────────────────────────────────────

def _cso_is_stub(entry: dict) -> bool:
    return not any(f in entry for f in CSO_FIELDS)


def _cso_existing_length(cso_val) -> int:
    if isinstance(cso_val, dict):
        return sum(len(str(v)) for v in cso_val.values())
    if isinstance(cso_val, str):
        return len(cso_val)
    return 0


def _cso_new_length(entry: dict) -> int:
    return sum(len(str(entry.get(f, ''))) for f in CSO_FIELDS)


def migrate_cso(dataweb: dict, cso_data: dict, canonical_to_t: dict) -> None:
    """Migrate CSO reports into canonical_archive entries where they improve coverage."""
    upgraded    = 0
    already_full = 0
    stubs       = 0
    not_found   = 0

    ca = dataweb.get('canonical_archive', {})

    for cid, artwork in ca.items():
        t_code = canonical_to_t.get(cid)
        if not t_code:
            not_found += 1
            continue

        entry = cso_data.get(t_code)
        if not entry:
            not_found += 1
            continue

        if _cso_is_stub(entry):
            stubs += 1
            continue

        existing_len = _cso_existing_length(artwork.get('cso'))
        new_len      = _cso_new_length(entry)

        if new_len > existing_len:
            artwork['cso'] = {
                f: entry[f] for f in CSO_FIELDS if not is_empty(entry.get(f))
            }
            upgraded += 1
        else:
            already_full += 1

    PIPELINE_REPORT['cso_upgraded']    = upgraded
    PIPELINE_REPORT['cso_already_full'] = already_full
    PIPELINE_REPORT['cso_stubs']       = stubs
    PIPELINE_REPORT['cso_not_found']   = not_found

    step_log(f"CSO upgraded: {upgraded} | already full: {already_full} | stubs: {stubs} | no T-code match: {not_found}")
    PIPELINE_REPORT['steps_completed'].append("Step 3: CSO Migration complete")


# ─────────────────────────────────────────────────────────────
# STEP 4: AUDIT AND PATCH FROM Q1 / CRUCIBLE MASTER
# ─────────────────────────────────────────────────────────────

def _get_from_sources(sources: list, *keys):
    """
    Search multiple source dicts (and their log_data / physical_reality sub-dicts)
    for the first non-empty value matching any key alias.
    """
    for src in sources:
        if not isinstance(src, dict):
            continue
        containers = [src]
        for sub in ('log_data', 'physical_reality'):
            if isinstance(src.get(sub), dict):
                containers.append(src[sub])
        for container in containers:
            for k in keys:
                val = container.get(k)
                if not is_empty(val):
                    return val
    return None


def patch_artwork(artwork: dict, q1: dict, crucible: dict) -> dict:
    """
    Fill empty fields in artwork from q1 and crucible sources.
    Never overwrites existing non-empty values.
    Returns dict of {field_name: 1} for each patched field.
    """
    patches = {}
    sources = [q1, crucible]

    # ── Root-level fields ────────────────────────────────────
    root_fields = [
        ('void',          ['void', 'void_type']),
        ('feibai',        ['feibai']),
        ('temporal',      ['temporal', 'temporal_quality']),
        ('st',            ['st', 'structural_types', 'structural_type']),
        ('edge_types',    ['edge_types', 'edge_type']),
        ('vec',           ['vec', 'primary_vector', 'vector']),
        ('cs',            ['cs', 'commitment_signal']),
        ('somatic_scale', ['somatic_scale', 'somatic']),
        ('w',             ['w', 'week']),
    ]
    for target, aliases in root_fields:
        if is_empty(artwork.get(target)):
            val = _get_from_sources(sources, *aliases)
            if val is not None:
                artwork[target] = val
                patches[target] = 1

    # ── log_data fields ──────────────────────────────────────
    if 'log_data' not in artwork or not isinstance(artwork['log_data'], dict):
        artwork['log_data'] = {}
    log = artwork['log_data']

    log_fields = [
        ('rating',               ['rating', 'Rating']),
        ('disposition',          ['disposition', 'Disposition']),
        ('hours',                ['hours', 'Hours']),
        ('surfaces',             ['surfaces', 'Surfaces']),
        ('mediums',              ['mediums', 'Mediums']),
        ('tools',                ['tools', 'Tools']),
        ('technical_observation', ['technical_observation', 'technical_intent',
                                   'Technical Intent', 'Technical Observation']),
    ]
    for target, aliases in log_fields:
        if is_empty(log.get(target)):
            val = _get_from_sources(sources, *aliases)
            if val is not None:
                log[target] = val
                patches[f'log_data.{target}'] = 1

    # ── physical_reality fields ──────────────────────────────
    if 'physical_reality' not in artwork or not isinstance(artwork['physical_reality'], dict):
        artwork['physical_reality'] = {}
    phys = artwork['physical_reality']

    phys_fields = [
        ('date',   ['date', 'Date']),
        ('height', ['height', 'Height', 'height_cm', 'Height (cm)']),
        ('width',  ['width', 'Width', 'width_cm', 'Width (cm)']),
    ]
    for target, aliases in phys_fields:
        if is_empty(phys.get(target)):
            val = _get_from_sources(sources, *aliases)
            if val is not None:
                phys[target] = val
                patches[f'physical_reality.{target}'] = 1

    return patches


def audit_and_patch(dataweb: dict, q1_data: dict, crucible_data: dict,
                    canonical_to_t: dict) -> None:
    """Patch gaps across all canonical_archive entries."""
    ca = dataweb.get('canonical_archive', {})
    total_patches = {}
    works_patched = 0

    for cid, artwork in ca.items():
        t_code   = canonical_to_t.get(cid, '')
        q1_entry = q1_data.get(t_code, {})      if t_code else {}
        cr_entry = crucible_data.get(t_code, {}) if t_code else {}

        patches = patch_artwork(artwork, q1_entry, cr_entry)
        if patches:
            works_patched += 1
            for field in patches:
                total_patches[field] = total_patches.get(field, 0) + 1

    PIPELINE_REPORT['patches_by_field'] = total_patches
    PIPELINE_REPORT['works_patched'] = works_patched

    step_log(f"Works patched: {works_patched}")
    if total_patches:
        step_log("Per-field patch counts:")
        for field, count in sorted(total_patches.items()):
            print(f"      {field}: {count}")
    else:
        step_log("No gaps found (all fields already populated, or source files missing)")

    PIPELINE_REPORT['steps_completed'].append("Step 4: Gap Patching complete")


# ─────────────────────────────────────────────────────────────
# STEP 5: REMOVE DEAD SCAFFOLDING
# ─────────────────────────────────────────────────────────────

def remove_scaffolding(dataweb: dict) -> None:
    """Remove empty scaffolding sections from dataweb."""
    removed = []

    # philosophical_nodes — always remove
    if 'philosophical_nodes' in dataweb:
        dataweb.pop('philosophical_nodes')
        removed.append('philosophical_nodes')
        step_log("Removed: philosophical_nodes")

    # orphaned_records — only if empty
    if 'orphaned_records' in dataweb:
        if is_empty(dataweb['orphaned_records']):
            dataweb.pop('orphaned_records')
            removed.append('orphaned_records (empty)')
            step_log("Removed: orphaned_records (was empty)")
        else:
            step_log(f"Kept: orphaned_records ({len(dataweb['orphaned_records'])} entries)")

    # orphaned_data — only if empty
    if 'orphaned_data' in dataweb:
        if is_empty(dataweb['orphaned_data']):
            dataweb.pop('orphaned_data')
            removed.append('orphaned_data (empty)')
            step_log("Removed: orphaned_data (was empty)")
        else:
            step_log(f"Kept: orphaned_data ({len(dataweb['orphaned_data'])} entries)")

    # W15 temporal_engine orphan placeholder
    te = dataweb.get('temporal_engine', {})
    if 'W15' in te:
        w15 = te['W15']
        if (w15.get('Status') == 'ORPHANED_WEEK_PENDING_TELEMETRY' or
                w15.get('status') == 'ORPHANED_WEEK_PENDING_TELEMETRY'):
            te.pop('W15')
            removed.append('temporal_engine.W15 (orphaned placeholder)')
            step_log("Removed: temporal_engine.W15 (was orphaned placeholder)")
        else:
            step_log("Kept: temporal_engine.W15 (has real telemetry data)")

    PIPELINE_REPORT['sections_removed'] = removed
    if not removed:
        step_log("Nothing to remove (sections absent or not empty)")
    PIPELINE_REPORT['steps_completed'].append("Step 5: Dead scaffolding removed")


# ─────────────────────────────────────────────────────────────
# STEP 6: UPGRADE ORACLE SYNTHESIS
# ─────────────────────────────────────────────────────────────

def _bool_val(v) -> bool:
    """Coerce various truthy representations to bool."""
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ('true', 'yes', '1')


def _week_num(week_str: str) -> int:
    m = re.search(r'(\d+)', str(week_str))
    return int(m.group(1)) if m else 9999


def compute_statistics(ca: dict) -> dict:
    """Compute aggregate statistics across all canonical_archive entries."""
    total = len(ca)
    if total == 0:
        return {}

    ratings       = []
    hours_list    = []
    killed        = 0
    saved         = 0
    feibai_count  = 0
    overwork_count = 0
    works_per_week = {}
    cso_full_count = 0
    cs_dist        = {}
    void_dist      = {}
    st_freq        = {}
    somatic_dist   = {}
    vec_dist       = {}

    for cid, aw in ca.items():
        log  = aw.get('log_data', {}) or {}

        # Rating
        rating = safe_float(log.get('rating') or aw.get('rating'))
        if rating is not None:
            ratings.append(rating)
            if rating <= 2:
                killed += 1
            else:
                saved += 1
        else:
            # Fallback: disposition text
            disp = str(log.get('disposition', '') or aw.get('disposition', '')).lower()
            if 'trash' in disp or ('kill' in disp and 'skill' not in disp):
                killed += 1

        # Hours
        h = safe_float(log.get('hours') or aw.get('hours'))
        if h is not None:
            hours_list.append(h)

        # Feibai
        if _bool_val(aw.get('feibai', False)):
            feibai_count += 1

        # Overworked
        if _bool_val(aw.get('overworked') or log.get('overworked') or False):
            overwork_count += 1

        # Week
        week = str(aw.get('w', '') or '').strip()
        if week:
            works_per_week[week] = works_per_week.get(week, 0) + 1

        # CSO coverage
        cso = aw.get('cso', {})
        if isinstance(cso, dict) and any(f in cso for f in CSO_FIELDS):
            cso_full_count += 1
        elif isinstance(cso, str) and len(cso) > 50:
            cso_full_count += 1

        # Commitment signal
        cs = aw.get('cs')
        if cs is not None:
            k = str(cs)
            cs_dist[k] = cs_dist.get(k, 0) + 1

        # Void type
        void = str(aw.get('void', '') or '').strip()
        if void:
            void_dist[void] = void_dist.get(void, 0) + 1

        # Structural types
        st = aw.get('st', [])
        if isinstance(st, str):
            st = [s.strip() for s in re.split(r'[;,]', st) if s.strip()]
        if isinstance(st, list):
            for s in st:
                s = str(s).strip()
                if s:
                    st_freq[s] = st_freq.get(s, 0) + 1

        # Somatic scale
        som = str(aw.get('somatic_scale', '') or '').strip()
        if som:
            somatic_dist[som] = somatic_dist.get(som, 0) + 1

        # Primary vector
        vec = str(aw.get('vec', '') or '').strip()
        if vec:
            vec_dist[vec] = vec_dist.get(vec, 0) + 1

    avg_rating  = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    total_hours = round(sum(hours_list), 1)
    kill_rate   = round(killed / total * 100, 1)
    save_rate   = round(saved  / total * 100, 1)
    feibai_rate = round(feibai_count  / total * 100, 1)
    ow_rate     = round(overwork_count / total * 100, 1)
    cso_cov     = round(cso_full_count / total * 100, 1)
    peak_week   = max(works_per_week, key=lambda k: works_per_week[k]) if works_per_week else None

    return {
        "total_crucible_works":         total,
        "total_studio_hours":           total_hours,
        "overall_kill_rate":            kill_rate,
        "overall_save_rate":            save_rate,
        "feibai_rate_overall":          feibai_rate,
        "overwork_rate_overall":        ow_rate,
        "avg_rating_overall":           avg_rating,
        "works_per_week":               works_per_week,
        "peak_production_week":         peak_week,
        "cso_coverage":                 cso_cov,
        "commitment_signal_distribution": cs_dist,
        "void_type_distribution":       void_dist,
        "structural_type_frequency":    st_freq,
        "somatic_scale_distribution":   somatic_dist,
        "vector_distribution":          vec_dist,
    }


def compute_material_ranking(ca: dict) -> list:
    """Rank substrates by save_rate descending."""
    sub_data = {}

    for cid, aw in ca.items():
        log = aw.get('log_data', {}) or {}

        # Collect surfaces
        surfaces = log.get('surfaces') or aw.get('surfaces', [])
        if isinstance(surfaces, str):
            surfaces = [s.strip() for s in re.split(r'[;,]', surfaces) if s.strip()]
        if not isinstance(surfaces, list):
            surfaces = []
        if not surfaces:
            continue

        rating    = safe_float(log.get('rating') or aw.get('rating'))
        hours     = safe_float(log.get('hours')  or aw.get('hours'))
        overworked = _bool_val(aw.get('overworked') or log.get('overworked') or False)
        feibai    = _bool_val(aw.get('feibai', False))

        for sub in surfaces:
            sub = str(sub).strip()
            if not sub:
                continue
            if sub not in sub_data:
                sub_data[sub] = {
                    'count': 0, 'saved': 0, 'killed': 0,
                    'ratings': [], 'hours': [], 'overworked': 0, 'feibai': 0,
                }
            d = sub_data[sub]
            d['count'] += 1
            if rating is not None:
                d['ratings'].append(rating)
                if rating >= 3:
                    d['saved'] += 1
                else:
                    d['killed'] += 1
            if hours is not None:
                d['hours'].append(hours)
            if overworked:
                d['overworked'] += 1
            if feibai:
                d['feibai'] += 1

    ranking = []
    for sub, d in sub_data.items():
        count  = d['count']
        rated  = d['saved'] + d['killed']
        sr = round(d['saved']    / rated  * 100, 1) if rated  > 0 else 0.0
        kr = round(d['killed']   / rated  * 100, 1) if rated  > 0 else 0.0
        ar = round(sum(d['ratings']) / len(d['ratings']), 2) if d['ratings'] else 0.0
        ah = round(sum(d['hours'])   / len(d['hours']),   1) if d['hours']   else 0.0
        or_ = round(d['overworked'] / count * 100, 1) if count > 0 else 0.0
        fr  = round(d['feibai']    / count * 100, 1) if count > 0 else 0.0
        ranking.append({
            "substrate":    sub,
            "name":         SUBSTRATE_NAMES.get(sub, sub),
            "count":        count,
            "save_rate":    sr,
            "kill_rate":    kr,
            "avg_rating":   ar,
            "avg_hours":    ah,
            "overwork_rate": or_,
            "feibai_rate":  fr,
        })

    ranking.sort(key=lambda x: x['save_rate'], reverse=True)
    if len(ranking) >= 1:
        ranking[0]['flag']  = 'TOP_PERFORMER'
    if len(ranking) >= 2:
        ranking[-1]['flag'] = 'WORST_PERFORMER'

    return ranking


def compute_temporal_momentum(ca: dict, temporal_engine: dict) -> dict:
    """Week-by-week statistics and momentum trend analysis."""

    # Group artworks by week
    week_artworks: dict = {}
    for cid, aw in ca.items():
        week = str(aw.get('w', '') or '').strip()
        if week:
            week_artworks.setdefault(week, []).append(aw)

    # Per-week stats
    week_stats = {}
    for week, artworks in week_artworks.items():
        ratings    = []
        hours_tot  = 0.0
        saved      = 0

        for aw in artworks:
            log = aw.get('log_data', {}) or {}
            r = safe_float(log.get('rating') or aw.get('rating'))
            if r is not None:
                ratings.append(r)
                if r >= 3:
                    saved += 1
            h = safe_float(log.get('hours') or aw.get('hours'))
            if h is not None:
                hours_tot += h

        # Step count from temporal_engine
        te = temporal_engine.get(week, {}) or {}
        step_count = (te.get('step_count') or te.get('steps'))
        if step_count is None:
            we = te.get('walking_engine')
            if isinstance(we, dict):
                step_count = we.get('step_count') or we.get('steps')

        week_stats[week] = {
            "works_count":  len(artworks),
            "avg_rating":   round(sum(ratings) / len(ratings), 2) if ratings else None,
            "save_rate":    round(saved / len(artworks) * 100, 1),
            "studio_hours": round(hours_tot, 1),
            "step_count":   safe_int(step_count),
        }

    sorted_weeks = sorted(week_stats.keys(), key=_week_num)
    first_3 = sorted_weeks[:3]
    last_3  = sorted_weeks[-3:]

    def avg_hours(weeks):
        vals = [week_stats[w]['studio_hours'] for w in weeks]
        return sum(vals) / len(vals) if vals else 0.0

    def avg_rat(weeks):
        vals = [week_stats[w]['avg_rating'] for w in weeks if week_stats[w]['avg_rating'] is not None]
        return sum(vals) / len(vals) if vals else 0.0

    f_hrs  = avg_hours(first_3)
    l_hrs  = avg_hours(last_3)
    f_rat  = avg_rat(first_3)
    l_rat  = avg_rat(last_3)

    hours_trend  = ('rising'  if l_hrs > f_hrs * 1.1
                    else 'falling' if l_hrs < f_hrs * 0.9
                    else 'stable')
    rating_trend = ('rising'  if l_rat > f_rat + 0.2
                    else 'falling' if l_rat < f_rat - 0.2
                    else 'stable')

    if hours_trend == rating_trend:
        overall_trend = hours_trend
    else:
        overall_trend = f"{hours_trend}_hours/{rating_trend}_ratings"

    inflection = None
    for w in sorted_weeks:
        ar = week_stats[w].get('avg_rating')
        if ar is not None and ar > 3.0:
            inflection = w
            break

    return {
        "week_by_week":    week_stats,
        "momentum_trend":  overall_trend,
        "hours_trend":     hours_trend,
        "rating_trend":    rating_trend,
        "inflection_week": inflection,
        "analysis": {
            "first_3_weeks":       first_3,
            "last_3_weeks":        last_3,
            "first_3_avg_hours":   round(f_hrs, 1),
            "last_3_avg_hours":    round(l_hrs, 1),
            "first_3_avg_rating":  round(f_rat, 2),
            "last_3_avg_rating":   round(l_rat, 2),
        },
    }


def upgrade_oracle(dataweb: dict) -> None:
    """Compute and inject statistics into oracle_synthesis."""
    ca = dataweb.get('canonical_archive', {})
    te = dataweb.get('temporal_engine', {})

    dataweb.setdefault('oracle_synthesis', {})
    oracle = dataweb['oracle_synthesis']

    step_log(f"Computing statistics from {len(ca)} works...")
    stats = compute_statistics(ca)
    oracle['computed_statistics'] = stats
    step_log(f"  total_works={stats.get('total_crucible_works')} | hours={stats.get('total_studio_hours')} | avg_rating={stats.get('avg_rating_overall')} | kill_rate={stats.get('overall_kill_rate')}% | cso_coverage={stats.get('cso_coverage')}%")

    step_log("Computing material performance ranking...")
    ranking = compute_material_ranking(ca)
    oracle['material_performance_ranking'] = ranking
    step_log(f"  {len(ranking)} substrates ranked")
    if ranking:
        step_log(f"  Top performer: {ranking[0]['substrate']} ({ranking[0]['name']}) — save_rate {ranking[0]['save_rate']}%")
        step_log(f"  Worst performer: {ranking[-1]['substrate']} ({ranking[-1]['name']}) — save_rate {ranking[-1]['save_rate']}%")

    step_log("Computing temporal momentum...")
    momentum = compute_temporal_momentum(ca, te)
    oracle['temporal_momentum'] = momentum
    step_log(f"  Weeks analyzed: {len(momentum.get('week_by_week', {}))} | trend: {momentum.get('momentum_trend')} | inflection: {momentum.get('inflection_week')}")

    PIPELINE_REPORT['oracle_fields_added'] = ['computed_statistics', 'material_performance_ranking', 'temporal_momentum']
    PIPELINE_REPORT['steps_completed'].append("Step 6: Oracle Synthesis upgraded")


# ─────────────────────────────────────────────────────────────
# STEP 7: UPDATE ARCHITECTURE META
# ─────────────────────────────────────────────────────────────

def update_architecture_meta(dataweb: dict) -> None:
    """Bump version, record timestamp and pipeline run details."""
    dataweb.setdefault('architecture_meta', {})
    meta = dataweb['architecture_meta']

    meta['version']      = "2.0"
    meta['timestamp']    = TODAY
    meta['last_updated'] = datetime.now().isoformat()

    meta['pipeline_run'] = {
        "run_date":            TODAY,
        "run_timestamp":       datetime.now().isoformat(),
        "script":              "neon_dataweb_pipeline.py",
        "steps_completed":     PIPELINE_REPORT['steps_completed'][:],
        "cso_entries_upgraded": PIPELINE_REPORT['cso_upgraded'],
        "cso_already_full":    PIPELINE_REPORT['cso_already_full'],
        "cso_stubs_skipped":   PIPELINE_REPORT['cso_stubs'],
        "id_bridge_count":     PIPELINE_REPORT['id_bridge_count'],
        "works_patched":       PIPELINE_REPORT['works_patched'],
        "patches_by_field":    PIPELINE_REPORT['patches_by_field'],
        "sections_removed":    PIPELINE_REPORT['sections_removed'],
        "oracle_fields_added": PIPELINE_REPORT['oracle_fields_added'],
    }

    meta['source_files'] = [
        INPUT_DATAWEB,
        INPUT_CSO_MASTER,
        INPUT_Q1,
        INPUT_CRUCIBLE,
        INPUT_CSV,
    ]

    step_log(f"Version → 2.0 | date: {TODAY}")
    PIPELINE_REPORT['steps_completed'].append("Step 7: Architecture meta updated")


# ─────────────────────────────────────────────────────────────
# STEP 8: WRITE OUTPUT
# ─────────────────────────────────────────────────────────────

def write_output(dataweb: dict) -> int:
    """Serialise to JSON, wrap in markdown fences, write to OUTPUT_FILE."""
    json_str = json.dumps(dataweb, indent=2, ensure_ascii=False)
    output   = f"```json\n{json_str}\n```\n"

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

    size    = os.path.getsize(OUTPUT_FILE)
    size_mb = size / (1024 * 1024)
    step_log(f"Written: {OUTPUT_FILE} — {size:,} bytes ({size_mb:.2f} MB)")
    PIPELINE_REPORT['steps_completed'].append("Step 8: Output written")
    return size


# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────

REQUIRED_STAT_FIELDS = [
    'total_crucible_works', 'total_studio_hours', 'overall_kill_rate',
    'overall_save_rate', 'feibai_rate_overall', 'overwork_rate_overall',
    'avg_rating_overall', 'works_per_week', 'peak_production_week',
    'cso_coverage', 'commitment_signal_distribution', 'void_type_distribution',
    'structural_type_frequency', 'somatic_scale_distribution', 'vector_distribution',
]


def validate_output(input_archive_count: int, input_file_size: int) -> None:
    """Re-parse output file and run all validation checks."""
    print()
    step_log("Re-parsing output for validation...")

    if not os.path.exists(OUTPUT_FILE):
        print("  [FAIL] Output file not found!")
        return

    output_size = os.path.getsize(OUTPUT_FILE)
    content     = read_file(OUTPUT_FILE)
    stripped    = strip_markdown_fences(content)

    # 1. JSON validity
    try:
        data = json.loads(stripped)
        print("  [PASS] JSON is valid")
    except json.JSONDecodeError as e:
        print(f"  [FAIL] JSON parse error: {e}")
        return

    # 2. canonical_archive count
    ca_count = len(data.get('canonical_archive', {}))
    if ca_count == input_archive_count:
        print(f"  [PASS] canonical_archive count: {ca_count} (matches input)")
    else:
        print(f"  [WARN] canonical_archive count: {ca_count} (input was {input_archive_count})")

    # 3. id_bridge
    bridge       = data.get('id_bridge', {})
    bridge_count = bridge.get('total_mapped', 0)
    if bridge_count > 0:
        print(f"  [PASS] id_bridge total_mapped: {bridge_count}")
    else:
        print(f"  [WARN] id_bridge total_mapped is 0 or missing")

    # 4. oracle_synthesis computed_statistics completeness
    oracle   = data.get('oracle_synthesis', {})
    stats    = oracle.get('computed_statistics', {})
    missing  = [f for f in REQUIRED_STAT_FIELDS if f not in stats]
    if not missing:
        print(f"  [PASS] oracle_synthesis.computed_statistics: all {len(REQUIRED_STAT_FIELDS)} fields present")
    else:
        print(f"  [WARN] oracle_synthesis.computed_statistics missing: {missing}")

    # 5. Spot-check 5 random entries
    ca = data.get('canonical_archive', {})
    if ca:
        sample = random.sample(list(ca.keys()), min(5, len(ca)))
        spot_ok = True
        for cid in sample:
            aw = ca[cid]
            for required in ('log_data', 'physical_reality'):
                if required not in aw:
                    print(f"  [WARN] Spot-check {cid}: missing '{required}'")
                    spot_ok = False
        if spot_ok:
            print(f"  [PASS] Spot-check 5 random entries ({', '.join(sample)}): all have log_data & physical_reality")

    # 6. File size sanity
    if output_size > input_file_size:
        print(f"  [PASS] Output size ({output_size:,} B) > input size ({input_file_size:,} B)")
    else:
        print(f"  [WARN] Output size ({output_size:,} B) is not larger than input ({input_file_size:,} B)")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    banner("NEON DATAWEB PIPELINE REPORT")
    print(f"  Run date : {TODAY}")
    print(f"  Output   : {OUTPUT_FILE}")
    print(f"  Python   : {sys.version.split()[0]}")
    print(f"  CWD      : {os.getcwd()}")

    input_file_size = os.path.getsize(INPUT_DATAWEB) if os.path.exists(INPUT_DATAWEB) else 0

    # ── Step 1: Parse all input files ──────────────────────────
    banner("Step 1: Parsing Input Files")
    dataweb       = parse_dataweb(INPUT_DATAWEB)
    t_to_can, can_to_t, can_to_sec, can_to_title = parse_csv_id_bridge(INPUT_CSV)
    cso_data      = parse_cso_master(INPUT_CSO_MASTER)
    q1_data       = parse_q1_dataweb(INPUT_Q1)
    crucible_data = parse_crucible_master(INPUT_CRUCIBLE)

    input_archive_count = len(dataweb.get('canonical_archive', {}))

    print(f"\n  ── Parse Summary ──────────────────────────")
    print(f"     Living Sovereign entries : {input_archive_count}")
    print(f"     ID bridge mappings       : {len(t_to_can)}")
    print(f"     CSO Master sections      : {len(cso_data)}")
    print(f"     Q1 artworks              : {len(q1_data)}")
    print(f"     Crucible trials          : {len(crucible_data)}")
    PIPELINE_REPORT['steps_completed'].append("Step 1: All input files parsed")

    # ── Step 2: Build ID Bridge ─────────────────────────────────
    banner("Step 2: Building ID Bridge")
    build_id_bridge(dataweb, t_to_can, can_to_t, can_to_sec, can_to_title)

    # ── Step 3: Migrate CSO Reports ─────────────────────────────
    banner("Step 3: CSO Report Migration")
    migrate_cso(dataweb, cso_data, can_to_t)

    # ── Step 4: Audit and Patch ─────────────────────────────────
    banner("Step 4: Gap Patching")
    audit_and_patch(dataweb, q1_data, crucible_data, can_to_t)

    # ── Step 5: Remove Dead Scaffolding ─────────────────────────
    banner("Step 5: Scaffolding Removal")
    remove_scaffolding(dataweb)

    # ── Step 6: Upgrade Oracle Synthesis ────────────────────────
    banner("Step 6: Oracle Synthesis Upgrade")
    upgrade_oracle(dataweb)

    # ── Step 7: Update Architecture Meta ────────────────────────
    banner("Step 7: Architecture Meta Update")
    update_architecture_meta(dataweb)

    # ── Step 8: Write Output ────────────────────────────────────
    banner("Step 8: Writing Output")
    output_size = write_output(dataweb)

    # ── Validation ──────────────────────────────────────────────
    banner("Validation")
    validate_output(input_archive_count, input_file_size)

    # ── Final Summary ────────────────────────────────────────────
    banner("PIPELINE COMPLETE")
    print(f"  Steps completed  : {len(PIPELINE_REPORT['steps_completed'])}")
    for s in PIPELINE_REPORT['steps_completed']:
        print(f"    \u2713 {s}")
    print()
    print(f"  CSO migration    : {PIPELINE_REPORT['cso_upgraded']} upgraded | "
          f"{PIPELINE_REPORT['cso_already_full']} already full | "
          f"{PIPELINE_REPORT['cso_stubs']} stubs skipped | "
          f"{PIPELINE_REPORT['cso_not_found']} no T-code match")
    print(f"  Gap patches      : {PIPELINE_REPORT['works_patched']} works patched")
    if PIPELINE_REPORT['patches_by_field']:
        for field, count in sorted(PIPELINE_REPORT['patches_by_field'].items()):
            print(f"    {field}: {count}")
    print(f"  Sections removed : {PIPELINE_REPORT['sections_removed']}")
    print(f"  Oracle fields    : {PIPELINE_REPORT['oracle_fields_added']}")
    print(f"  Output size      : {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
    print()
    print("=" * 60)
    print("=== COMPLETE ===")
    print("=" * 60)


if __name__ == "__main__":
    main()
