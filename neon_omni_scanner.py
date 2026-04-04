import os
import glob
import json
import csv
import re

# ==============================================================================
# PETER YUILL STUDIO DATAWEB - OMNI-SCANNER V6.1 (AUDITOR'S MASTER PATCH)
# ARCHITECT: Niwcjeje (Bangkok, 2026)
# PROJECT: Forensic Overrides, Absolute Scrubbing, & Temporal Narrative
# ==============================================================================

# FORENSIC OVERRIDES: The CSV is flawed. The Visual Forensics file is absolute.
FORENSIC_OVERRIDES = {
    "T_011": {"Surfaces": "S5"}, # Overriding CSV's S6 claim
    "T_082": {"Surfaces": "S6"}  # Overriding CSV's S7 claim based on card in photo
}

def scan_csv_dna_and_find_header(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        for i in range(5):
            line = f.readline().lower()
            if not line: break
            if "jester_activity" in line or "weather_report" in line or "walking_engine" in line:
                return "TELEMETRY", i
            elif "disposition" in line and "mediums" in line:
                return "PHYSICAL_FOOTPRINT", i
    return "UNKNOWN", 0

def breathe_and_evolve(directory=".", base_archive="00_GLOBAL_SOVEREIGN_ARCHIVE_V1.json"):
    print(f"Initiating Omni-Scan V6.1. Loading Base Archive: [{base_archive}]")

    if not os.path.exists(base_archive):
        print(f"CRITICAL ERROR: {base_archive} not found.")
        return

    with open(base_archive, 'r', encoding='utf-8') as f:
        dataweb = json.load(f)

    for node in ["temporal_engine", "philosophical_nodes", "orphaned_data"]:
        if node not in dataweb: dataweb[node] = {}

    # ==========================================================================
    # 1. CSV INGESTION (With Forensic Overrides & Unrestricted Temporal Mapping)
    # ==========================================================================
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    for filepath in csv_files:
        dna, header_row_index = scan_csv_dna_and_find_header(filepath)

        if dna != "UNKNOWN":
            with open(filepath, 'r', encoding='utf-8') as f:
                for _ in range(header_row_index): next(f)
                dict_reader = csv.DictReader(f)

                for row in dict_reader:
                    # Strip whitespace but PRESERVE all headers (no stripping keys that might drop narrative)
                    clean_row = {str(k).strip(): str(v).strip() for k, v in row.items() if k and str(k).strip()}

                    if dna == "TELEMETRY":
                        week_val = clean_row.get("Week", "")
                        # Hard Stop
                        if "CRUCIBLE TRIALS" in week_val or week_val.startswith("T_") or week_val == "Trial_Code":
                            break

                        try:
                            week_int = int(week_val)
                            if week_int > 0:
                                week_id = f"W{week_int}"
                                if week_id not in dataweb["temporal_engine"]:
                                    dataweb["temporal_engine"][week_id] = {}
                                # Full unlobotomized update (preserves Raw_Weather_Report, etc.)
                                dataweb["temporal_engine"][week_id].update(clean_row)
                                dataweb["temporal_engine"][week_id].pop("Status", None)
                                dataweb["temporal_engine"][week_id].pop("System_Note", None)
                        except ValueError:
                            continue

                    elif dna == "PHYSICAL_FOOTPRINT":
                        code = clean_row.get("Code", "")
                        if not code: continue

                        # Apply Forensic Truths over CSV flaws
                        if code in FORENSIC_OVERRIDES:
                            clean_row.update(FORENSIC_OVERRIDES[code])

                        target_cid = None
                        for cid, art_data in dataweb.get("canonical_archive", {}).items():
                            if art_data.get("provenance", {}).get("original_studio_code") == code:
                                target_cid = cid
                                break

                        if target_cid:
                            clean_row.pop("Code", None)

                            if "log_data" not in dataweb["canonical_archive"][target_cid]:
                                dataweb["canonical_archive"][target_cid]["log_data"] = {}

                            log_ref = dataweb["canonical_archive"][target_cid]["log_data"]

                            # Map specific metrics elegantly
                            log_ref["disposition"] = clean_row.pop("Disposition", log_ref.get("disposition", ""))
                            log_ref["rating"] = clean_row.pop("Rating", log_ref.get("rating", ""))
                            log_ref["hours"] = clean_row.pop("Hours", log_ref.get("hours", ""))
                            log_ref["technical_intent"] = clean_row.pop("Technical Intent", log_ref.get("technical_intent", ""))
                            log_ref["discovery"] = clean_row.pop("Discovery", log_ref.get("discovery", ""))

                            surfaces = clean_row.pop("Surfaces", "")
                            if surfaces: log_ref["surfaces"] = [s.strip() for s in surfaces.split(";") if s.strip()]

                            mediums = clean_row.pop("Mediums", "")
                            if mediums: log_ref["mediums"] = [m.strip() for m in mediums.split(";") if m.strip()]

                            tools = clean_row.pop("Tools", "")
                            if tools: log_ref["tools"] = [t.strip() for t in tools.split(";") if t.strip()]

                            # Dump remaining unstructured physical footprint
                            if "physical_reality" not in dataweb["canonical_archive"][target_cid]:
                                dataweb["canonical_archive"][target_cid]["physical_reality"] = {}
                            if clean_row:
                                dataweb["canonical_archive"][target_cid]["physical_reality"].update(clean_row)
                        else:
                            dataweb["orphaned_data"][code] = clean_row

    # ==========================================================================
    # 2. MARKDOWN INGESTION (Anti-Cannibalism)
    # ==========================================================================
    md_files = glob.glob(os.path.join(directory, "*.md"))
    nav_pattern = re.compile(r'\[\[NAV_P_\d{3}\]\]')
    sec_pattern = re.compile(r'\[\[SEC_[a-zA-Z0-9_]+\]\]')

    for filepath in md_files:
        filename = os.path.basename(filepath)
        if "DATAWEB" in filename or filename.startswith("00_GLOBAL_SOVEREIGN_ARCHIVE") or "DATABASE" in filename:
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            dataweb["philosophical_nodes"][filename] = {
                "referenced_nav_texts": list(set(nav_pattern.findall(content))),
                "referenced_sec_zones": list(set(sec_pattern.findall(content))),
                "byte_mass": len(content),
                "raw_text_ledger": content
            }

    # ==========================================================================
    # 3. GLOBAL RUTHLESS SCRUB & TEMPORAL ANCHORING (The Master Cleanup)
    # ==========================================================================
    ghost_keys_to_nest = ["Rating", "Disposition", "Hours", "Surfaces", "Mediums", "Tools", "Date", "Technical Intent", "Discovery"]

    for cid, art_data in dataweb.get("canonical_archive", {}).items():
        # A. Strip legacy root redundancy
        art_data.pop("disp", None)
        art_data.pop("r", None)
        art_data.pop("Code", None)

        # B. Sanitize Markdown Brackets everywhere
        if "sec" in art_data:
            art_data["sec"] = str(art_data["sec"]).replace("[[", "").replace("]]", "")
        if "provenance" in art_data and "sec_routing_tag" in art_data["provenance"]:
            tag = str(art_data["provenance"]["sec_routing_tag"])
            art_data["provenance"]["sec_routing_tag"] = tag.replace("[[", "").replace("]]", "")

        # C. Hunt for capitalized CSV keys mistakenly placed at root in previous bad runs
        if "log_data" not in art_data: art_data["log_data"] = {}
        for ghost in ghost_keys_to_nest:
            if ghost in art_data:
                # Move to nested dict and lowercase the key
                art_data["log_data"][ghost.lower().replace(" ", "_")] = art_data.pop(ghost)

        # D. W15 Orphan Crisis Resolution
        w_tag = art_data.get("w", "")
        if w_tag and str(w_tag).startswith("W"):
            if w_tag not in dataweb["temporal_engine"]:
                dataweb["temporal_engine"][w_tag] = {
                    "Status": "ORPHANED_WEEK_PENDING_TELEMETRY",
                    "System_Note": f"Placeholder auto-generated via cid {cid} to secure temporal anchor.",
                    "Raw_Weather_Report": "Awaiting physical telemetry."
                }

    with open("LIVING_SOVEREIGN_DATAWEB.json", 'w', encoding='utf-8') as f:
        json.dump(dataweb, f, indent=2, ensure_ascii=False)

    print("\nV6.1 Execution Complete. The Masterpiece is secured.")

if __name__ == "__main__":
    breathe_and_evolve()
