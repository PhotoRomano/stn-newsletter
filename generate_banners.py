#!/usr/bin/env python3
"""Generate this week's watercolor section banners via Higgsfield.

Usage: python3 generate_banners.py <issue-date, e.g. 2026-10-01> [--force]

Reads banner_prompts.json for style + per-section prompts, generates one
banner per section via the `higgsfield` CLI at the widest aspect ratio the
model supports, center-crops it down to a skinny letterbox strip
(crop_aspect_ratio in the config -- the model can't natively produce
anything that wide), and saves each under assets/banners/<slug>/<date>.png.
Never overwrites a prior week's image unless --force is passed -- every
week's set is kept, matching the "each issue gets a permanent page"
archival policy this repo already follows for the newsletter pages
themselves.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent
CONFIG_PATH = REPO / "banner_prompts.json"

# The higgsfield CLI's status/response layer is flaky (intermittent HTTP 503s
# and dropped "no response received" errors even after the job completes
# server-side) -- confirmed 2026-09-29, two of three jobs that reported a
# CLI-side failure had actually finished fine per `higgsfield generate list`.
# Retry the create call, and if it still errors, fall back to matching the
# prompt against the most recent completed jobs before giving up.
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 10
RECOVERY_LOOKUP_LIMIT = 10


def load_config():
    return json.loads(CONFIG_PATH.read_text())


def find_result_url(obj):
    """Walk the higgsfield --json job object for a media URL."""
    if isinstance(obj, dict):
        for key in ("url", "result_url", "media_url", "output_url", "image_url"):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
        for v in obj.values():
            found = find_result_url(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_result_url(item)
            if found:
                return found
    return None


def recover_via_recent_jobs(prompt):
    """Look for a completed job matching this exact prompt, in case the CLI
    dropped the response after the job actually finished server-side."""
    proc = subprocess.run(
        ["higgsfield", "generate", "list", "--json"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        jobs = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    for job in jobs[:RECOVERY_LOOKUP_LIMIT]:
        if job.get("status") != "completed":
            continue
        if job.get("params", {}).get("prompt") == prompt:
            url = job.get("result_url") or find_result_url(job)
            if url:
                return url
    return None


def generate_one(model, aspect_ratio, prompt):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        proc = subprocess.run(
            [
                "higgsfield", "generate", "create", model,
                "--prompt", prompt,
                "--aspect_ratio", aspect_ratio,
                "--wait", "--json",
            ],
            capture_output=True, text=True,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                url = find_result_url(data)
                if url:
                    return url
                last_error = f"no media URL found in higgsfield response: {proc.stdout[:500]}"
            except json.JSONDecodeError:
                last_error = f"could not parse higgsfield --json output: {proc.stdout[:500]}"
        else:
            last_error = f"higgsfield CLI failed (exit {proc.returncode}): {proc.stdout}{proc.stderr}"

        # The job may have completed server-side even though the CLI call
        # above errored out client-side -- check before treating it as a
        # real failure and burning another attempt/credit.
        recovered = recover_via_recent_jobs(prompt)
        if recovered:
            print(f"       (recovered via generate list after CLI-side error: {last_error.strip()})")
            return recovered

        if attempt < MAX_ATTEMPTS:
            print(f"       attempt {attempt}/{MAX_ATTEMPTS} failed ({last_error.strip()}), retrying in {RETRY_DELAY_SECONDS}s...")
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(f"gave up after {MAX_ATTEMPTS} attempts: {last_error}")


def parse_ratio(ratio_str):
    w, h = ratio_str.split(":")
    return float(w) / float(h)


def center_crop_to_ratio(path, target_ratio):
    """Crop the image in place to target_ratio (width/height), keeping the
    vertical center (the prompt asks the model to keep subjects in the
    middle third of the frame for exactly this crop)."""
    with Image.open(path) as img:
        w, h = img.size
        current_ratio = w / h
        if current_ratio > target_ratio:
            # too wide already (shouldn't happen given source ratios) -- crop width
            new_w = round(h * target_ratio)
            left = (w - new_w) // 2
            box = (left, 0, left + new_w, h)
        else:
            new_h = round(w / target_ratio)
            top = (h - new_h) // 2
            box = (0, top, w, top + new_h)
        img.crop(box).save(path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    date = sys.argv[1]
    force = "--force" in sys.argv[2:]

    config = load_config()
    model = config["model"]
    aspect_ratio = config["aspect_ratio"]
    crop_ratio = parse_ratio(config["crop_aspect_ratio"])
    style = config["style"]
    negative = config.get("negative_prompt", "")

    results = {}
    for section in config["sections"]:
        slug = section["slug"]
        out_dir = REPO / "assets" / "banners" / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date}.png"

        if out_path.exists() and not force:
            print(f"[skip] {slug}: {out_path} already exists (use --force to regenerate)")
            results[slug] = str(out_path)
            continue

        full_prompt = f"{style} {section['prompt']}"
        if negative:
            full_prompt += f" Avoid: {negative}."

        print(f"[gen]  {slug}: submitting to {model} ({aspect_ratio})...")
        url = generate_one(model, aspect_ratio, full_prompt)
        urllib.request.urlretrieve(url, out_path)
        center_crop_to_ratio(out_path, crop_ratio)
        print(f"[done] {slug}: saved {out_path} (cropped to {config['crop_aspect_ratio']})")
        results[slug] = str(out_path)

    print("\nGenerated banners:")
    for slug, path in results.items():
        rel = Path(path).relative_to(REPO)
        print(f"  {slug}: https://photoromano.github.io/stn-newsletter/{rel}")


if __name__ == "__main__":
    main()
