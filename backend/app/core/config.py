import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file() -> None:
    project_env = Path(__file__).resolve().parents[3] / ".env"
    if project_env.exists():
        for line in project_env.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    backend_env = Path(__file__).resolve().parents[2] / ".env"
    if backend_env.exists():
        for line in backend_env.read_text(encoding="utf-8").splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    host: str
    port: int
    qwen_api_key: str | None
    qwen_base_url: str
    qwen_model: str


def get_settings() -> Settings:
    load_env_file()
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://root:password@127.0.0.1:3306/agenthub",
        ),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8088")),
        qwen_api_key=os.getenv("QWEN_API_KEY"),
        qwen_base_url=os.getenv(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        qwen_model=os.getenv("QWEN_MODEL", "qwen-plus"),
    )
