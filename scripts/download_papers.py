"""
Download papers from Sci-Hub by DOI.
Two-step: (1) get Sci-Hub page, extract PDF storage URL, (2) download PDF with Referer.
"""
import urllib.request
import ssl, re, time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
KB_DIR = BASE_DIR / "data" / "knowledge" / "raw_sources" / "academic_literature"

MIRRORS = ["https://sci-hub.ru", "https://sci-hub.st", "https://sci-hub.wf"]

# All papers to download: (doi, filename_label, domain)
PAPERS = [
    # === P0: injury_rehab (6) ===
    ("10.1007/s40279-015-0370-y", "van_der_Worp_2015_Injury_Review", "injury_rehab"),
    ("10.2519/jospt.2019.0302", "Willy_2019_PFPS_CPG", "injury_rehab"),
    ("10.2519/jospt.2018.0302", "Silbernagel_2018_Achilles_CPG", "injury_rehab"),
    ("10.2519/jospt.2014.0303", "Martin_2014_Plantar_Fasciitis_CPG", "injury_rehab"),
    ("10.1136/bjsports-2018-100157", "Taberner_2019_Return_to_Sport", "injury_rehab"),
    ("10.1136/bjsports-2015-095788", "Gabbett_2016_ACWR_Paradox", "injury_rehab"),
    # === P0 extra: injury_rehab ===
    ("10.4085/1062-6050-43.5.509", "Lopes_2012_Running_MSK_Injuries", "injury_rehab"),
    ("10.1136/bjsports-2015-095733", "Drew_2016_Load_Management", "injury_rehab"),

    # === P1: training_methodology (4) ===
    ("10.1123/ijspp.5.3.276", "Seiler_2010_TID_Best_Practice", "training_methodology"),
    ("10.3389/fphys.2014.00033", "Stoggl_2014_Polarized_vs_Threshold", "training_methodology"),
    ("10.1249/01.MSS.0000053163.74175.A7", "Mujika_2003_Tapering", "training_methodology"),
    ("10.1249/MSS.0b013e318279a10a", "Meeusen_2013_Overtraining", "training_methodology"),
    # === P1 extra: training ===
    ("10.1007/s40279-019-01248-0", "Blagrove_2020_Strength_Running_Economy_Meta", "training_methodology"),
    ("10.2165/00007256-200737100-00004", "Midgley_2007_Marathon_Physiology", "training_methodology"),

    # === P1: nutrition (2) ===
    ("10.1249/MSS.0000000000000852", "Thomas_2016_ACSM_Nutrition", "nutrition_hydration"),
    ("10.1186/s12970-018-0242-y", "Kreider_2018_ISSN_Sports_Nutrition", "nutrition_hydration"),
]

ctx = ssl.create_default_context()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def download_one(doi: str, label: str, domain: str) -> int:
    """Download paper from Sci-Hub. Returns size in bytes, 0 on failure."""
    dest = KB_DIR / domain / f"{label}.pdf"
    if dest.exists() and dest.stat().st_size > 50000:
        return -dest.stat().st_size  # negative = already exists

    for mirror in MIRRORS:
        try:
            # Step 1: Fetch Sci-Hub page
            page_url = f"{mirror}/{doi}"
            req = urllib.request.Request(page_url, headers=HEADERS)
            resp = urllib.request.urlopen(req, context=ctx, timeout=30)
            html = resp.read().decode("utf-8", errors="ignore")

            if len(html) < 500 or "Just a moment" in html:
                continue

            # Step 2: Find PDF storage URL
            m = re.search(r'(?:src|href)\s*=\s*"([^"]*\.pdf[^"]*)"', html)
            if not m:
                m = re.search(r'<iframe[^>]*src\s*=\s*"([^"]+)"', html)
            if not m:
                continue

            pdf_path = m.group(1)
            if pdf_path.startswith("//"):
                pdf_url = "https:" + pdf_path
            elif pdf_path.startswith("/"):
                pdf_url = mirror + pdf_path
            else:
                pdf_url = pdf_path

            # Step 3: Download PDF with Referer
            req2 = urllib.request.Request(pdf_url, headers={**HEADERS, "Referer": page_url})
            resp2 = urllib.request.urlopen(req2, context=ctx, timeout=60)
            content = resp2.read()

            if len(content) > 50000:
                dest.write_bytes(content)
                return len(content)

        except Exception:
            continue

    return 0


def main():
    for d in ["injury_rehab", "training_methodology", "nutrition_hydration"]:
        (KB_DIR / d).mkdir(parents=True, exist_ok=True)

    results = {"ok": [], "skip": [], "fail": []}
    for doi, label, domain in PAPERS:
        print(f"[{domain[:6]:6s}] {label:45s}", end=" ", flush=True)
        size = download_one(doi, label, domain)
        if size > 0:
            results["ok"].append((label, domain, size))
            print(f"OK  {size//1024:4d} KB")
        elif size < 0:
            results["skip"].append((label, domain, -size))
            print(f"SKIP ({(-size)//1024} KB)")
        else:
            results["fail"].append((label, domain))
            print("FAIL")
        time.sleep(0.8)

    print(f"\n{'='*65}")
    print(f"OK: {len(results['ok'])} | SKIP: {len(results['skip'])} | FAIL: {len(results['fail'])}")
    print(f"{'='*65}")
    for label, domain, size in results["ok"]:
        print(f"  [{domain}] {label} ({size//1024} KB)")
    if results["fail"]:
        print(f"\nFAILED:")
        for label, domain in results["fail"]:
            print(f"  [{domain}] {label}")


if __name__ == "__main__":
    main()
