import asyncio
import os
import socket
from pathlib import Path


ROOT_MARKERS = (".git", "apps", "data", "marathon_qa_assistant", "vector_kb")


def _looks_like_repo_root(path: Path) -> bool:
    # 优先识别马拉松助手项目根，避免父级 git 仓库把 data 路径带偏。
    return (path / "apps").exists() and (path / "data").exists()


def _walk_for_repo_root(start: Path) -> Path | None:
    current = start.absolute()
    candidates = [current, *current.parents]
    for candidate in candidates:
        if _looks_like_repo_root(candidate):
            return candidate
    return None


def _get_base_dir() -> Path:
    """Return the repository root without resolving Windows junction paths."""
    if os.environ.get("PROJECT_ROOT"):
        return Path(os.environ["PROJECT_ROOT"]).absolute()

    for start in (Path.cwd(), Path(__file__).absolute()):
        root = _walk_for_repo_root(start if start.is_dir() else start.parent)
        if root is not None:
            return root

    return Path.cwd().absolute()


BASE_DIR = _get_base_dir()
DATA_DIR = Path(os.environ.get("MARATHON_DATA_DIR", BASE_DIR / "data")).absolute()
RESEARCH_DIR = BASE_DIR / "research"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

STAI_DIR = RESEARCH_DIR / "stai2026"
STAI_MANUSCRIPT_DIR = STAI_DIR / "manuscript"
STAI_BENCHMARK_DIR = STAI_DIR / "benchmark"
STAI_ANALYSIS_DIR = STAI_DIR / "analysis"
STAI_RUNS_DIR = ARTIFACTS_DIR / "research_runs" / "stai2026"

MEXRXBENCH_DIR = RESEARCH_DIR / "mexrxbench"

DEFAULT_VECTOR_DIR = DATA_DIR / "vector_kb" / "default"
V2_VECTOR_DIR = DATA_DIR / "vector_kb" / "v2"
USER_PROFILE_PATH = DEFAULT_VECTOR_DIR / "user_profile.json"
USER_VECTOR_DIR = DATA_DIR / "vector_kb" / "user"
UPLOAD_DOCS_DIR = DATA_DIR / "uploads" / "seed"

LEGACY_DEFAULT_VECTOR_DIR = BASE_DIR / "vector_kb"
LEGACY_UPLOAD_DOCS_DIR = BASE_DIR / "uploaded_docs"
LEGACY_USER_VECTOR_DIR = BASE_DIR / "vector_kb_user"
LEGACY_STAI_DIR = BASE_DIR / "docs" / "paper_project"

RUNTIME_DATA_DIR = Path(
    os.environ.get("MARATHON_RUNTIME_DATA_DIR", BASE_DIR.parent / "_runtime_data" / BASE_DIR.name)
).absolute()
RUNTIME_UPLOAD_DOCS_DIR = RUNTIME_DATA_DIR / "uploaded_docs"
RUNTIME_USER_VECTOR_DIR = RUNTIME_DATA_DIR / "vector_kb_user"
GOOGLE_CREDENTIALS_PATH = RUNTIME_DATA_DIR / "google_credentials.json"

def has_vector_kb_artifacts(vector_dir: Path) -> bool:
    """
    判断指定目录是否具备可加载的完整知识库产物。
    必须同时具备 chunks.jsonl 和 FAISS 索引文件。
    """
    chunks_file = vector_dir / "chunks.jsonl"
    faiss_index = vector_dir / "faiss_db" / "index.faiss"
    return chunks_file.exists() and faiss_index.exists()

def get_preferred_vector_dir() -> Path:
    """
    返回当前应优先加载的向量库目录。
    Monorepo 新路径优先，旧根目录路径保留一轮兼容。
    """
    for candidate in (
        USER_VECTOR_DIR,
        V2_VECTOR_DIR,
        RUNTIME_USER_VECTOR_DIR,
        LEGACY_USER_VECTOR_DIR,
        DEFAULT_VECTOR_DIR,
        LEGACY_DEFAULT_VECTOR_DIR,
    ):
        if has_vector_kb_artifacts(candidate):
            return candidate
    return DEFAULT_VECTOR_DIR

# 全局知识图谱高亮词
DEFAULT_HIGHLIGHTS = [
    "gradual increment", "maximal values are reached", "lifestyles",
    "quality and efficiency of the training process and competitive performance",
    "prevention programs", "into the training process and competition schedules"
]

# 共享全局状态 (避免循环引用)
class GlobalState:
    def __init__(self):
        self.chunks = []
        self.kb_chunks_len = 0
        self.kb_source = "unknown"
        self.kb_health_reason = ""

global_state = GlobalState()

async def check_ollama_status():
    """检查 Ollama 服务是否在线"""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    host = ollama_url.split("//")[-1].split(":")[0]
    port = int(ollama_url.split(":")[-1])
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2.0)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def pick_free_port(host: str, preferred_port: int | None, max_tries: int = 50) -> int:
    """自动寻找空闲端口"""
    if preferred_port is None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return int(s.getsockname()[1])
    start = int(preferred_port)
    for port in range(start, start + int(max_tries)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, int(port)))
                return int(port)
        except OSError:
            continue
    raise OSError(f"Cannot find empty port in range: {start}-{start + int(max_tries) - 1}")
