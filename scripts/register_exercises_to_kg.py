"""将动作库训练动作注册到知识图谱。

从 vector_kb_user/chunks.jsonl 中筛选动作库条目，
解析 name/categories/objective，注册为 workout_template 节点。
支持幂等运行（按 chunk_id 去重）。
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def sha1_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def parse_exercise_from_chunk(chunk: dict) -> dict:
    """从单个 chunk 的 text 字段解析训练动作信息。"""
    text = chunk.get("text", "")

    result = {
        "name": "",
        "categories": [],
        "objective": "",
        "chunk_id": chunk.get("chunk_id", ""),
    }

    name_match = re.search(r'name[：:]\s*(.+?)(?:\n|$)', text)
    if name_match:
        result["name"] = name_match.group(1).strip()

    cat_match = re.search(r'categories\s*[：:]\s*(.+?)(?:\n\S|$)', text, re.DOTALL)
    if cat_match:
        raw = cat_match.group(1).strip()
        result["categories"] = [c.strip() for c in re.split(r'[,，]', raw) if c.strip()]

    obj_match = re.search(r'objective\s*[：:]\s*(.+?)(?:\n\S|\Z)', text, re.DOTALL)
    if obj_match:
        result["objective"] = obj_match.group(1).strip()

    return result


def register_exercises(chunks: list[dict], kg_path: Path) -> dict:
    """将动作库 chunk 列表注册到知识图谱 JSON 文件。幂等。"""
    if kg_path.exists():
        kg = json.loads(kg_path.read_text(encoding="utf-8"))
    else:
        kg = {"nodes": {}, "edges": []}

    existing_ids = set(kg["nodes"].keys())
    added_nodes = 0
    added_edges = 0

    for chunk in chunks:
        if chunk.get("source_file") != "动作库.pdf":
            continue

        info = parse_exercise_from_chunk(chunk)
        if not info["name"]:
            continue

        node_id = sha1_hash("动作库_" + info["name"])

        if node_id in existing_ids:
            continue

        kg["nodes"][node_id] = {
            "label": info["name"],
            "type": "workout_template",
            "source_chunks": [info["chunk_id"]],
            "properties": {
                "categories": info["categories"],
                "objective": info["objective"],
            },
        }
        existing_ids.add(node_id)
        added_nodes += 1

        for cat in info["categories"]:
            cat_id = sha1_hash("category_" + cat)
            if cat_id not in existing_ids:
                kg["nodes"][cat_id] = {
                    "label": cat,
                    "type": "category",
                    "source_chunks": [],
                }
                existing_ids.add(cat_id)

            kg["edges"].append({
                "source": node_id,
                "target": cat_id,
                "relation": "has_category",
                "canonical_relation": "has_category",
                "evidence": {
                    "source": "动作库.pdf",
                    "chunk_id": info["chunk_id"],
                    "text_span": chunk.get("text", "")[:200],
                    "confidence": 1.0,
                },
            })
            added_edges += 1

    kg_path.write_text(
        json.dumps(kg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "total_nodes": len(kg["nodes"]),
        "total_edges": len(kg["edges"]),
        "added_nodes": added_nodes,
        "added_edges": added_edges,
    }


def main():
    parser = argparse.ArgumentParser(description="注册动作库训练动作到知识图谱")
    parser.add_argument(
        "--chunks-path",
        default="vector_kb_user/chunks.jsonl",
        help="chunks.jsonl 路径",
    )
    parser.add_argument(
        "--kg-path",
        default="vector_kb/knowledge_graph.json",
        help="knowledge_graph.json 路径",
    )
    args = parser.parse_args()

    chunks_path = Path(args.chunks_path).absolute()
    kg_path = Path(args.kg_path).absolute()

    if not chunks_path.exists():
        print(f"[ERROR] chunks 文件不存在: {chunks_path}")
        sys.exit(1)

    chunks = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))

    result = register_exercises(chunks, kg_path)

    print(f"注册完成: +{result['added_nodes']} nodes, +{result['added_edges']} edges")
    print(f"KG 总计: {result['total_nodes']} nodes, {result['total_edges']} edges")


if __name__ == "__main__":
    main()
