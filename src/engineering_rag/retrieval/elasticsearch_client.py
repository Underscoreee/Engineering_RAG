"""Elasticsearch connection settings and client construction."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


DEFAULT_INDEX_NAME = "engineering_rag_chunks_v1"


class ElasticsearchSettings(BaseModel):
    """Connection settings loaded from environment variables by CLIs."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)
    index_name: str = Field(default=DEFAULT_INDEX_NAME, min_length=1)
    username: str | None = None
    password: str | None = None

    @model_validator(mode="after")
    def validate_credentials(self) -> "ElasticsearchSettings":
        if bool(self.username) != bool(self.password):
            raise ValueError(
                "ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD must be set together"
            )
        return self

    @classmethod
    def from_env(cls) -> "ElasticsearchSettings":
        url = os.getenv("ELASTICSEARCH_URL")
        if not url:
            raise ValueError("ELASTICSEARCH_URL is required")
        return cls(
            url=url,
            index_name=os.getenv("ELASTICSEARCH_INDEX", DEFAULT_INDEX_NAME),
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
        )


def create_elasticsearch_client(settings: ElasticsearchSettings) -> Any:
    """Build the official synchronous client without hard-coded credentials."""

    from elasticsearch import Elasticsearch

    options: dict[str, Any] = {}
    if settings.username and settings.password:
        options["basic_auth"] = (settings.username, settings.password)
    return Elasticsearch(settings.url, **options)
