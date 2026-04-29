import os
import json
import re
from pathlib import Path

# 使用相对路径，以脚本所在目录为基准
BASE_DIR = Path(__file__).parent.resolve()
INDEX_PATH = BASE_DIR / "vector_kb" / "chunks.jsonl"

REQUIRED_CONCEPTS = {
    "第一周": ["Week 1", "Week1", "First Week"],
    "周计划": ["Weekly Plan", "Training Schedule", "Weekly Schedule"],
    "训练大纲": ["Training Syllabus", "Training Outline"],
    "阈值跑": ["Threshold Run", "T-Pace", "Threshold Pace"],
    "乳酸阈值": ["Lactate Threshold", "LTHR"],
    "课表": ["Session", "Workout", "Schedule"],
    "处方": ["Prescription", "Dosage"],
    "强度设定": ["Intensity", "Zone Setting"],
    "心率区间": ["Heart Rate Zone", "HR Zone"],
    "恢复原则": ["Recovery Principle", "Rest Day"]
}

# 与 workflow_engine.py 一致的强特征正则 (1480c39 增强版)
WEEKLY_PATTERN = r"(周[一二三四五六日]|monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon\b|tue\b|wed\b|thu\b|fri\b|sat\b|sun\b|第[1-9一二三四五六七八九十]周|day\s*\d+|session\s*\d+|workout\s*\d+|microcycle)"
PRESCRIPTION_PATTERN = r"(\d+(\.\d+)?\s*(km|公里|公里/小时|bpm|次/分)|[1-9]\d{0,2}[:：][0-5]\d\s*(min/km|/km|配速))"
STRUCTURE_PATTERN = r"(\d+\s*[xX*×]\s*\d+|间歇|重复|组|循环|次|组数)"
NUMERIC_PRESCRIPTION_PATTERN = r"(\d+[:：]\d+\s*(min/km|/km)|[1-9]\d{1,2}\s*bpm)"

def check_kb_readiness():
    if not os.path.exists(INDEX_PATH):
        print(f"[ERROR] Index file not found: {INDEX_PATH}")
        return

    try:
        chunks = []
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))
        
        print(f"Total Chunks in KB: {len(chunks)}")
        
        if not chunks:
            print("[WARN] Knowledge base is empty!")
            return

        found_counts = {concept: 0 for concept in REQUIRED_CONCEPTS}
        
        # 强特征统计
        weekly_hits = 0
        prescription_hits = 0
        structure_hits = 0
        numeric_hits = 0
        plan_ready_chunks = 0
        
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            
            # 基础关键词检查
            for concept, synonyms in REQUIRED_CONCEPTS.items():
                if concept.lower() in text or any(syn.lower() in text for syn in synonyms):
                    found_counts[concept] += 1
            
            # 强特征正则检查
            has_weekly = bool(re.search(WEEKLY_PATTERN, text))
            has_prescription = bool(re.search(PRESCRIPTION_PATTERN, text))
            has_structure = bool(re.search(STRUCTURE_PATTERN, text))
            has_numeric = bool(re.search(NUMERIC_PRESCRIPTION_PATTERN, text))
            
            if has_weekly: weekly_hits += 1
            if has_prescription: prescription_hits += 1
            if has_structure: structure_hits += 1
            if has_numeric: numeric_hits += 1
            
            # 联合命中检查 (Plan Readiness) - 与 Evidence-First 2.0 逻辑一致
            if has_weekly and (has_prescription or has_structure or has_numeric):
                plan_ready_chunks += 1
        
        print("\n[1] Keyword Analysis Results:")
        print("-" * 40)
        missing = []
        for concept, count in found_counts.items():
            status = "[OK]" if count > 0 else "[MISSING]"
            print(f"{status} {concept.ljust(15)}: {count} matches")
            if count == 0:
                missing.append(concept)
        
        print("\n[2] Structural Feature Analysis (Evidence Gate Simulation):")
        print("-" * 40)
        print(f"Weekly Structure Patterns: {weekly_hits} matches")
        print(f"Prescription Patterns:     {prescription_hits} matches")
        print(f"Workout Structure Patterns: {structure_hits} matches")
        print(f"Numeric Pace/HR Patterns:  {numeric_hits} matches")
        print(f"Plan-Ready Chunks:         {plan_ready_chunks} matches (Weekly + Evidence in same chunk)")
        
        print("-" * 40)
        
        # 综合判定
        if plan_ready_chunks > 0:
            print("Conclusion: KB is READY for 'Week 1 Plan' (Evidence Gate will PASS).")
        elif weekly_hits > 0 and (prescription_hits > 0 or structure_hits > 0):
            print("Conclusion: KB has potential evidence, but it is split across chunks. (Evidence Gate might pass depending on top_k).")
        else:
            print("Conclusion: KB is INCOMPLETE for Plan Generation (Evidence Gate will BLOCK).")
            
        if missing:
            print(f"\nMissing core concepts: {', '.join(missing)}")
            print("Action: Add PDF/Markdown files containing these keywords and structural patterns.")

    except Exception as e:
        print(f"[ERROR] Failed to read index: {str(e)}")

if __name__ == "__main__":
    check_kb_readiness()
