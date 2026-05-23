import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
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
