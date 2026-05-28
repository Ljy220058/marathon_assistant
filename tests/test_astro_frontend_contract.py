"""Astro frontend contract tests.

Covers: index.astro DOM ids, data attributes, script entry points,
API key safety, build output integrity.
"""

import re
import sys
from pathlib import Path
from typing import List


root = Path(__file__).parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

ASTRO_PAGE = root / "apps" / "web" / "src" / "pages" / "index.astro"
APP_SCRIPT = root / "apps" / "web" / "src" / "scripts" / "app.js"


def _read_stripped(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _file_lines(path: Path) -> List[str]:
    return _read_stripped(path).splitlines()


# ---- P0.1: DOM id contract ----

REQUIRED_DOM_IDS = [
    "runQuery",
    "calendar",
    "dayModal",
    "evidenceDrawer",
    "statusPanel",
    "adjustmentHistory",
]


def test_astro_page_contains_all_required_dom_ids():
    content = _read_stripped(ASTRO_PAGE)
    for dom_id in REQUIRED_DOM_IDS:
        assert f'id="{dom_id}"' in content or f"id='{dom_id}'" in content, (
            f"Missing DOM id '{dom_id}' in index.astro"
        )


# ---- P0.1: Data attributes contract ----

REQUIRED_DATA_ATTRIBUTES = [
    "data-plan-generation-entry",
    "data-calendar-view",
]


def test_astro_page_contains_required_data_attributes():
    content = _read_stripped(ASTRO_PAGE)
    for attr in REQUIRED_DATA_ATTRIBUTES:
        assert attr in content, f"Missing data attribute '{attr}' in index.astro"


# ---- Script entry point ----

def test_astro_page_imports_app_js():
    content = _read_stripped(ASTRO_PAGE)
    assert 'src="../scripts/app.js"' in content or "src='../scripts/app.js'" in content, (
        "index.astro must import app.js as script entry"
    )


# ---- P1.8: No localStorage API key persistence ----

def test_frontend_script_does_not_persist_api_key():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.setItem("marathon_ds_api_key"' not in content
    assert "localStorage.setItem('marathon_ds_api_key'" not in content


def test_frontend_script_does_not_get_api_key_from_storage():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.getItem("marathon_ds_api_key"' not in content
    assert "localStorage.getItem('marathon_ds_api_key'" not in content


def test_frontend_script_clears_old_api_key_on_startup():
    content = _read_stripped(APP_SCRIPT)
    assert 'localStorage.removeItem("marathon_ds_api_key"' in content


# ---- API base endpoint references ----

def test_api_client_references_correct_endpoints():
    content = _read_stripped(APP_SCRIPT)
    endpoints = ["/query", "/feedback", "/plans", "/health", "/profile"]
    found = [ep for ep in endpoints if ep in content]
    assert len(found) >= 3, f"Missing expected API endpoints: {set(endpoints) - set(found)}"


# ---- Calendar section ----

def test_calendar_section_has_correct_layout():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="calendar-section"' in content
    assert 'id="calendarCount"' in content
    assert 'class="calendar-grid"' in content


# ---- Day modal ----

def test_day_modal_has_correct_structure():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="dayModal"' in content
    assert 'id="dayModalBackdrop"' in content
    assert 'id="dayModalContent"' in content
    assert 'id="dayModalClose"' in content


# ---- Evidence drawer ----

def test_evidence_drawer_has_correct_structure():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="evidenceDrawer"' in content
    assert 'id="evidenceDrawerContent"' in content


# ---- Feedback modal / status panel ----

def test_status_and_adjustment_sections_exist():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="statusPanel"' in content
    assert 'id="adjustmentHistory"' in content


# ---- Query input and controls ----

def test_query_input_and_controls_exist():
    content = _read_stripped(ASTRO_PAGE)
    assert 'id="queryInput"' in content
    assert 'id="dsApiKey"' in content
    assert 'id="saveDsApiKey"' in content
    assert 'id="clearDsApiKey"' in content


# ---- Nav links ----

def test_navigation_links_point_to_correct_sections():
    content = _read_stripped(ASTRO_PAGE)
    for section in ["plan", "calendar-section", "profile", "evidence"]:
        assert f'"{section}"' in content, f"Missing nav link href to {section}"


def test_api_key_label_warns_no_persistence():
    content = _read_stripped(ASTRO_PAGE)
    assert "会话" in content or "不保留" in content or "不写入" in content, (
        "API key section should warn that keys are not persisted"
    )
