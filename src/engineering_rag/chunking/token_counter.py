"""A small deterministic token estimate that can be replaced later."""

import re


class TokenCounter:
    """Count CJK characters, word groups, and punctuation as approximate tokens."""

    _TOKEN = re.compile(r"[\u3400-\u9fff]|[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|[^\w\s]", re.UNICODE)

    def count(self, text: str) -> int:
        """Return a deterministic approximate token count for ``text``."""

        return sum(1 for _ in self._TOKEN.finditer(text))
