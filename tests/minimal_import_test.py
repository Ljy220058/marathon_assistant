import sys
import os
from pathlib import Path

# Add project root to sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

def run_import_checks():
    print("Testing core imports...")
    try:
        from marathon_qa_assistant.core.workflow import integrated_app
        print("[SUCCESS] Core workflow imported successfully.")
    except Exception as e:
        print(f"[FAILURE] Core workflow import failed: {e}")
        return False

    print("Testing node imports...")
    nodes = [
        "security", "router", "profile_and_retrieval", 
        "plan_nodes", "expert_nodes", "output_nodes"
    ]
    for node in nodes:
        try:
            # We use importlib or direct import since they are in nodes/
            exec(f"from marathon_qa_assistant.nodes import {node}")
            print(f"[SUCCESS] Node '{node}' imported successfully.")
        except Exception as e:
            print(f"[FAILURE] Node '{node}' import failed: {e}")
            return False

    print("Testing UI imports...")
    try:
        from marathon_qa_assistant.ui.legacy_ui import UIHelper
        print("[SUCCESS] Legacy UI components imported successfully.")
    except Exception as e:
        print(f"[FAILURE] UI import failed: {e}")
        return False

    print("Testing service imports...")
    services = ["vector_store", "knowledge_graph", "multimodal"]
    for svc in services:
        try:
            exec(f"from marathon_qa_assistant.services import {svc}")
            print(f"[SUCCESS] Service '{svc}' imported successfully.")
        except Exception as e:
            print(f"[FAILURE] Service '{svc}' import failed: {e}")
            return False

    return True


def test_imports():
    assert run_import_checks() is True

if __name__ == "__main__":
    success = run_import_checks()
    if success:
        print("\nAll critical components imported successfully!")
        sys.exit(0)
    else:
        print("\nCritical component import failed.")
        sys.exit(1)
