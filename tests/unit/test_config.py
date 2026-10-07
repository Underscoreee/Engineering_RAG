from engineering_rag.config import AppConfig, load_config


def test_config_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("ENGINEERING_RAG_ENV", raising=False)
    monkeypatch.delenv("ENGINEERING_RAG_LOG_LEVEL", raising=False)

    assert load_config() == AppConfig(environment="development", log_level="INFO")


def test_config_reads_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("ENGINEERING_RAG_ENV", "test")
    monkeypatch.setenv("ENGINEERING_RAG_LOG_LEVEL", "debug")

    config = load_config()

    assert config.environment == "test"
    assert config.log_level == "DEBUG"
