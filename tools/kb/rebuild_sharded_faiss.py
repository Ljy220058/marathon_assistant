"""
rebuild_sharded_faiss.py
========================
从 v2_sharded/ 各分片的 chunks.jsonl 重建 FAISS 向量索引。

适用场景
--------
- 修改了 chunks.jsonl（新增、删除、去重）之后
- 不需要重新抓取 PDF / 重新分块
- 只需重新生成 faiss_db/ 目录

依赖
----
运行环境必须与 API server 相同（conda 环境）：
    conda activate <your_env>          # torch 2.5.1 + faiss-gpu/cpu
    cd <project_root>
    python tools/kb/rebuild_sharded_faiss.py

Ollama 必须在本地运行并已拉取 bge-m3:latest：
    ollama pull bge-m3:latest

用法
----
# 重建所有分片（耗时较长）
python tools/kb/rebuild_sharded_faiss.py

# 只重建指定分片（推荐：仅重建修改过的）
python tools/kb/rebuild_sharded_faiss.py --shards nutrition medical_safety sport_psychology

# 指定 Ollama 地址
python tools/kb/rebuild_sharded_faiss.py --ollama-url http://localhost:11434

# dry-run：只打印会做什么，不实际构建
python tools/kb/rebuild_sharded_faiss.py --dry-run
"""

import argparse
import io
import json
import logging
import sys
import time
from pathlib import Path

# Windows GBK 终端不能输出 Unicode，统一转成 UTF-8 输出流
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 项目根目录 & 模块路径 ────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
BACKEND_SRC = PROJECT_ROOT / "apps" / "backend" / "src"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

# ── 日志 ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rebuild_sharded_faiss")

ALL_SHARDS = [
    "training_protocol",
    "nutrition",
    "injury_safety",
    "medical_safety",
    "sport_psychology",
]

V2_SHARDED_DEFAULT = PROJECT_ROOT / "data" / "vector_kb" / "v2_sharded"


def load_jsonl(path: Path) -> list[dict]:
    chunks = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("跳过第 %d 行（JSON 解析失败）: %s", lineno, e)
    return chunks


def rebuild_one_shard(
    shard_name: str,
    shard_dir: Path,
    *,
    dry_run: bool = False,
    ollama_url: str = "http://localhost:11434",
) -> dict:
    """重建单个分片的 FAISS 索引，返回结果摘要。"""
    chunks_file = shard_dir / "chunks.jsonl"
    faiss_dir = shard_dir / "faiss_db"
    result = {"shard": shard_name, "ok": False, "chunks": 0, "elapsed_s": 0.0, "error": ""}

    if not chunks_file.exists():
        result["error"] = f"chunks.jsonl 不存在: {chunks_file}"
        logger.error("[%s] %s", shard_name, result["error"])
        return result

    chunks = load_jsonl(chunks_file)
    result["chunks"] = len(chunks)

    # 过滤空文本（Ollama 对空字符串返回空 embedding 会导致 FAISS 崩溃）
    valid_chunks = [c for c in chunks if str(c.get("text") or "").strip()]
    skipped = len(chunks) - len(valid_chunks)
    if skipped:
        logger.warning("[%s] 跳过 %d 个空 text chunk", shard_name, skipped)

    if not valid_chunks:
        result["error"] = "所有 chunk 均为空 text，跳过"
        logger.error("[%s] %s", shard_name, result["error"])
        return result

    logger.info("[%s] 准备重建: %d chunks（%d 有效）→ %s", shard_name, len(chunks), len(valid_chunks), faiss_dir)

    if dry_run:
        logger.info("[%s] DRY-RUN: 跳过实际构建", shard_name)
        result["ok"] = True
        return result

    # ── 动态 import（需要 conda 环境已激活）─────────────────────────────────
    try:
        import os
        os.environ.setdefault("OLLAMA_BASE_URL", ollama_url)

        from marathon_qa_assistant.services.vector_store import save_outputs, load_chunks as _lc  # noqa: F401
    except ImportError as e:
        result["error"] = f"import 失败（确认 conda 环境已激活）: {e}"
        logger.error("[%s] %s", shard_name, result["error"])
        return result

    t0 = time.time()
    try:
        saved = save_outputs(shard_dir, valid_chunks, None, None, None)
        result["ok"] = True
        result["elapsed_s"] = round(time.time() - t0, 1)
        logger.info(
            "[%s] ✓ 重建完成，耗时 %.1fs，向量数 %s",
            shard_name,
            result["elapsed_s"],
            saved.get("faiss_vector_count", "?"),
        )
    except Exception as e:
        result["error"] = str(e)
        result["elapsed_s"] = round(time.time() - t0, 1)
        logger.error("[%s] ✗ 重建失败: %s", shard_name, e)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 chunks.jsonl 重建 v2_sharded FAISS 向量索引",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--shards",
        nargs="+",
        default=None,
        choices=ALL_SHARDS,
        metavar="SHARD",
        help=f"要重建的分片（默认全部）。可选: {', '.join(ALL_SHARDS)}",
    )
    parser.add_argument(
        "--shard-base",
        default=str(V2_SHARDED_DEFAULT),
        help=f"v2_sharded 根目录（默认: {V2_SHARDED_DEFAULT}）",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API 地址（默认: http://localhost:11434）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要做什么，不实际构建",
    )
    args = parser.parse_args()

    shards_to_rebuild = args.shards or ALL_SHARDS
    shard_base = Path(args.shard_base)

    if not shard_base.exists():
        logger.error("v2_sharded 目录不存在: %s", shard_base)
        sys.exit(1)

    if args.dry_run:
        logger.info("=== DRY-RUN 模式 ===")

    logger.info("将重建 %d 个分片: %s", len(shards_to_rebuild), ", ".join(shards_to_rebuild))
    logger.info("Ollama URL: %s", args.ollama_url)
    logger.info("分片根目录: %s", shard_base)
    print()

    # ── 连通性预检 ────────────────────────────────────────────────────────────
    if not args.dry_run:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{args.ollama_url}/api/tags", timeout=5) as resp:
                tags = json.loads(resp.read().decode())
                model_names = [m["name"] for m in tags.get("models", [])]
                bge_models = [n for n in model_names if "bge-m3" in n]
                if not bge_models:
                    logger.warning("⚠ Ollama 未找到 bge-m3 模型。已有模型: %s", model_names)
                    logger.warning("  请先运行: ollama pull bge-m3:latest")
                else:
                    logger.info("✓ Ollama 连通，bge-m3 模型已就绪: %s", bge_models)
        except Exception as e:
            logger.error("✗ 无法连接 Ollama (%s): %s", args.ollama_url, e)
            logger.error("  请先启动 Ollama，然后重试")
            sys.exit(1)

    # ── 逐分片重建 ────────────────────────────────────────────────────────────
    results = []
    total_t0 = time.time()

    for shard_name in shards_to_rebuild:
        shard_dir = shard_base / shard_name
        if not shard_dir.exists():
            logger.warning("[%s] 目录不存在，跳过: %s", shard_name, shard_dir)
            results.append({"shard": shard_name, "ok": False, "error": "目录不存在"})
            continue
        r = rebuild_one_shard(shard_name, shard_dir, dry_run=args.dry_run, ollama_url=args.ollama_url)
        results.append(r)
        print()

    # ── 汇总 ─────────────────────────────────────────────────────────────────
    total_elapsed = round(time.time() - total_t0, 1)
    ok_count = sum(1 for r in results if r["ok"])
    fail_count = len(results) - ok_count

    print("=" * 60)
    print(f"重建完成: {ok_count}/{len(results)} 成功，总耗时 {total_elapsed}s")
    print("=" * 60)
    for r in results:
        status = "✓" if r["ok"] else "✗"
        detail = f"{r.get('chunks', 0)} chunks, {r.get('elapsed_s', 0):.1f}s" if r["ok"] else r.get("error", "")
        print(f"  {status} {r['shard']:<22}  {detail}")

    if fail_count:
        print(f"\n{fail_count} 个分片失败，请查看上方日志")
        sys.exit(1)

    # ── 更新 shard_meta.json 的重建时间戳 ────────────────────────────────────
    if not args.dry_run and ok_count > 0:
        meta_path = shard_base / "shard_meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            from datetime import datetime
            meta["last_faiss_rebuild_at"] = datetime.now().isoformat()
            meta["last_rebuilt_shards"] = shards_to_rebuild
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("✓ shard_meta.json 已更新 last_faiss_rebuild_at")


if __name__ == "__main__":
    main()
