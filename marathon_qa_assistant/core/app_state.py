import asyncio
import os
import shutil
import socket
from pathlib import Path

# 获取项目根目录，优先使用当前工作目录以避免 Junction/Symlink 路径解析问题
def _get_base_dir() -> Path:
    # 如果设置了环境变量，优先使用
    if os.environ.get("PROJECT_ROOT"):
        return Path(os.environ["PROJECT_ROOT"])
    
    # 尝试从当前文件路径获取，但不使用 resolve() 以保留 Junction 路径
    try:
        # __file__ 通常是绝对路径或相对于启动目录的路径
        pkg_root = Path(__file__).absolute().parents[1]
        base = pkg_root.parent
        
        # 验证基础目录是否包含关键标识（如 vector_kb）
        if (base / "vector_kb").exists():
            return base
    except Exception:
        pass
        
    # 回退到当前工作目录
    return Path.cwd()

BASE_DIR = _get_base_dir()
DEFAULT_VECTOR_DIR = BASE_DIR / "vector_kb"
USER_PROFILE_PATH = DEFAULT_VECTOR_DIR / "user_profile.json"
RUNTIME_DATA_DIR = BASE_DIR.parent / "_runtime_data" / BASE_DIR.name
LEGACY_UPLOAD_DOCS_DIR = BASE_DIR / "uploaded_docs"
LEGACY_USER_VECTOR_DIR = BASE_DIR / "vector_kb_user"
UPLOAD_DOCS_DIR = RUNTIME_DATA_DIR / "uploaded_docs"
USER_VECTOR_DIR = RUNTIME_DATA_DIR / "vector_kb_user"

def _seed_runtime_dir(legacy_dir: Path, runtime_dir: Path) -> None:
    """
    将运行期可变数据迁移到项目根目录外，避免 Chainlit `-w` 监听到写盘后自触发重载。
    首次迁移时保留旧目录内容，后续统一使用新目录。
    """
    runtime_dir.parent.mkdir(parents=True, exist_ok=True)
    if runtime_dir.exists():
        return
    if legacy_dir.exists():
        shutil.copytree(legacy_dir, runtime_dir, dirs_exist_ok=True)
    else:
        runtime_dir.mkdir(parents=True, exist_ok=True)

_seed_runtime_dir(LEGACY_UPLOAD_DOCS_DIR, UPLOAD_DOCS_DIR)
_seed_runtime_dir(LEGACY_USER_VECTOR_DIR, USER_VECTOR_DIR)

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
    若用户知识库已构建完成，则优先使用 `vector_kb_user`；
    否则回退到默认知识库 `vector_kb`。
    """
    if has_vector_kb_artifacts(USER_VECTOR_DIR):
        return USER_VECTOR_DIR
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
