"""Build retrieval context without altering original chunk content."""

from collections.abc import Iterable


class ContextHeaderBuilder:
    """Format standard and structural metadata as a separate text header."""

    def build(
        self,
        *,
        standard_name: str | None,
        standard_code: str | None,
        chapter: str | None,
        section: str | None,
        clause_number: str | None,
        section_path: Iterable[str] = (),
    ) -> str:
        lines: list[str] = []
        if standard_name and standard_code:
            lines.append(f"《{standard_name}》（{standard_code}）")
        elif standard_name:
            lines.append(f"《{standard_name}》")
        elif standard_code:
            lines.append(f"（{standard_code}）")

        values = [value for value in section_path if value]
        if not values:
            values = [value for value in (chapter, section, clause_number) if value]
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                lines.append(f"> {value}")
                seen.add(value)
        return "\n".join(lines)
