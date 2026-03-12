#!/usr/bin/env python3
"""
Seed all training pipeline phases with correct dependencies into Tripod Console.

Usage:
    # Dry run (prints what would be created, no API calls)
    python scripts/seed_phases.py --dry-run

    # Against local backend
    python scripts/seed_phases.py --base-url http://localhost:8000

    # Against production
    python scripts/seed_phases.py --base-url https://tripod-backend.shemaywam.com

    # Clean existing phases first, then recreate
    python scripts/seed_phases.py --base-url https://tripod-backend.shemaywam.com --clean

    # Skip login prompt (pass credentials directly)
    python scripts/seed_phases.py --base-url https://tripod-backend.shemaywam.com \\
        --email admin@shemaywam.com --password yourpass
"""

import argparse
import getpass
import sys

import requests

# ──────────────────────────────────────────────────────────────────────────────
# Phase definitions: (key, name, description)
# ──────────────────────────────────────────────────────────────────────────────
PHASES = [
    (
        "data_collection",
        "Data Collection",
        "Collect raw audio recordings from native speakers (100+ hours of natural speech: "
        "stories, dialogues, procedural speech) and Bible audio (MP3s). No transcription "
        "required. Uses the Oral Capture app (Flutter, offline-first) with predefined "
        "genre/category tagging and per-language duration tracking.",
    ),
    (
        "audio_segmentation",
        "Audio Segmentation",
        "Split raw MP3 recordings into 2-10 second WAV segments (mono, 16 kHz) via silence "
        "detection (RMS energy < -40 dB, minimum silence gap 0.5 s). Normalize loudness, "
        "resample, and upload segments to Modal cloud volume (bible-audio-data). "
        "Scripts: segment_audio.py → upload_to_modal.py.",
    ),
    (
        "acoustic_tokenization",
        "Acoustic Tokenization",
        "Extract frame-level features from audio segments using a self-supervised speech model "
        "(MMS-300M or XEUS) and cluster into 100 discrete acoustic units via MiniBatchKMeans. "
        "Produces timestamped unit sequences per segment and a fitted K-Means model. "
        "Runs on A10G GPU via Modal. Script: phase1_acoustic.py.",
    ),
    (
        "bpe_motif_discovery",
        "BPE Motif Discovery",
        "Train a SentencePiece BPE tokenizer on acoustic unit sequences to discover 500-1000 "
        "recurring acoustic motifs — analogous to morphological building blocks of the language. "
        "BPE encoding is reversible (decode is deterministic and lossless). "
        "Runs on CPU. Script: phase2_bpe.py.",
    ),
    (
        "vocoder_training",
        "Vocoder Training",
        "Train HiFi-GAN V2 (Generator + Multi-Period/Multi-Scale Discriminator) to convert "
        "discrete acoustic units + pitch bins into 16 kHz waveform audio. Uses pitch "
        "conditioning (F0 via pyin, 32 bins), MRF fusion, and compound loss (45x mel L1 + "
        "2x multi-res STFT + 2x feature matching + adversarial). Runs on A100 GPU via "
        "Modal. Script: phase3_vocoder_v2.py.",
    ),
    (
        "conversational_tagging",
        "Conversational Tagging (AViTA)",
        "Human-in-the-loop semantic tagging via the AViTA app. A facilitator asks ontology-aligned "
        "plain-language questions, a native speaker isolates the relevant sound span, and the "
        "facilitator 'paints' ontology tags onto BPE motif spans with precise timestamps. "
        "Active learning selects high-value clips. Produces aligned training dataset (.pt) with "
        "timestamped semantic-acoustic anchors.",
    ),
    (
        "generative_training",
        "Generative Model Training",
        "Train a Seq2Seq Transformer that maps semantic token sequences (from Meaning Maps) to "
        "acoustic motif sequences (from AViTA alignment). The model learns motif selection under "
        "semantic constraints, oral-language ordering patterns, and pragmatic realization. "
        "Cross-entropy loss on target motif prediction.",
    ),
]

# ──────────────────────────────────────────────────────────────────────────────
# Dependency definitions: phase_key → [depends_on_key, ...]
# ──────────────────────────────────────────────────────────────────────────────
DEPENDENCIES = {
    "data_collection": [],
    "audio_segmentation": ["data_collection"],
    "acoustic_tokenization": ["audio_segmentation"],
    "bpe_motif_discovery": ["acoustic_tokenization"],
    "vocoder_training": ["acoustic_tokenization"],
    "conversational_tagging": ["bpe_motif_discovery"],
    "generative_training": ["conversational_tagging"],
}


def login(base_url: str, email: str, password: str) -> str:
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    token = resp.json()["tokens"]["access_token"]
    print(f"Authenticated as {email}")
    return token


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fetch_existing_phases(base_url: str, headers: dict) -> list[dict]:
    resp = requests.get(f"{base_url}/api/phases", headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def delete_phase(base_url: str, headers: dict, phase_id: str, name: str):
    resp = requests.delete(f"{base_url}/api/phases/{phase_id}", headers=headers, timeout=15)
    if resp.status_code == 204:
        print(f"  Deleted: {name}")
    else:
        print(f"  Failed to delete {name} ({resp.status_code}): {resp.text}")


def create_phase(base_url: str, headers: dict, name: str, description: str) -> str | None:
    resp = requests.post(
        f"{base_url}/api/phases",
        headers=headers,
        json={"name": name, "description": description},
        timeout=15,
    )
    if resp.status_code == 201:
        phase_id = resp.json()["id"]
        print(f"  Created: {name} ({phase_id})")
        return phase_id
    else:
        print(f"  Failed to create {name} ({resp.status_code}): {resp.text}")
        return None


def add_dependency(base_url: str, headers: dict, phase_id: str, depends_on_id: str, label: str):
    resp = requests.post(
        f"{base_url}/api/phases/{phase_id}/dependencies",
        headers=headers,
        json={"depends_on_id": depends_on_id},
        timeout=15,
    )
    if resp.status_code == 201:
        print(f"  Linked: {label}")
    else:
        print(f"  Failed to link {label} ({resp.status_code}): {resp.text}")


def dry_run():
    print("\n=== DRY RUN — Phases to create ===\n")
    for i, (key, name, desc) in enumerate(PHASES, 1):
        deps = DEPENDENCIES.get(key, [])
        dep_names = [n for k, n, _ in PHASES if k in deps]
        print(f"  {i:2d}. {name}")
        print(f"      {desc[:90]}...")
        print(f"      Depends on: {', '.join(dep_names) if dep_names else '(none)'}")
        print()

    print("=== Dependency Graph (text) ===\n")
    print(
        "  Data Collection → Audio Segmentation → Acoustic Tokenization"
        " ─┬→ BPE Motif Discovery → Conversational Tagging (AViTA)"
        " → Generative Model Training"
    )
    print("                                                                 └→ Vocoder Training")
    print()
    total_edges = sum(len(v) for v in DEPENDENCIES.values())
    print(f"Total: {len(PHASES)} phases, {total_edges} dependency edges")


def main():
    parser = argparse.ArgumentParser(
        description="Seed training pipeline phases into Tripod Console",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend API base URL",
    )
    parser.add_argument("--email", help="Admin email (prompted if not provided)")
    parser.add_argument("--password", help="Admin password (prompted if not provided)")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete ALL existing phases before seeding",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print phases and exit (no API calls)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip phases that already exist by name (default: true)",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    # Auth
    email = args.email or input("Admin email: ")
    password = args.password or getpass.getpass("Admin password: ")
    token = login(args.base_url, email, password)
    headers = get_headers(token)

    # Clean if requested
    if args.clean:
        print("\n--- Cleaning existing phases ---")
        existing = fetch_existing_phases(args.base_url, headers)
        if not existing:
            print("  No existing phases to delete.")
        for phase in existing:
            delete_phase(args.base_url, headers, phase["id"], phase["name"])

    # Fetch existing phases (after potential clean) to enable skip-by-name
    existing = fetch_existing_phases(args.base_url, headers)
    existing_by_name = {p["name"]: p["id"] for p in existing}

    # Create phases
    print(f"\n--- Creating {len(PHASES)} phases ---")
    key_to_id: dict[str, str] = {}

    for key, name, description in PHASES:
        if name in existing_by_name:
            key_to_id[key] = existing_by_name[name]
            print(f"  Exists: {name} ({existing_by_name[name]})")
        else:
            phase_id = create_phase(args.base_url, headers, name, description)
            if phase_id:
                key_to_id[key] = phase_id

    # Create dependencies
    print("\n--- Setting dependencies ---")
    dep_count = 0
    for key, dep_keys in DEPENDENCIES.items():
        if key not in key_to_id:
            continue
        phase_id = key_to_id[key]
        phase_name = next(n for k, n, _ in PHASES if k == key)
        for dep_key in dep_keys:
            if dep_key not in key_to_id:
                print(f"  Skipped: {phase_name} → {dep_key} (dependency not found)")
                continue
            dep_id = key_to_id[dep_key]
            dep_name = next(n for k, n, _ in PHASES if k == dep_key)
            label = f"{phase_name} → depends on → {dep_name}"
            add_dependency(args.base_url, headers, phase_id, dep_id, label)
            dep_count += 1

    print(f"\n--- Done! Created/verified {len(key_to_id)} phases with {dep_count} dependencies ---")


if __name__ == "__main__":
    main()
