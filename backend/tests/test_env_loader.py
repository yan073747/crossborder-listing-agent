import os

from env_loader import load_env_file


def test_load_env_file_reads_key_value_pairs(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SKIP_DOTENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
LLM_API_KEY="test-api-key"
LLM_MODEL=deepseek-v4-flash
# ignored comment
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    load_env_file(env_file)

    assert os.environ["LLM_API_KEY"] == "test-api-key"
    assert os.environ["LLM_MODEL"] == "deepseek-v4-flash"


def test_load_env_file_does_not_override_existing_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SKIP_DOTENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_MODEL=deepseek-v4-flash\n", encoding="utf-8")
    monkeypatch.setenv("LLM_MODEL", "existing-model")

    load_env_file(env_file)

    assert os.environ["LLM_MODEL"] == "existing-model"
