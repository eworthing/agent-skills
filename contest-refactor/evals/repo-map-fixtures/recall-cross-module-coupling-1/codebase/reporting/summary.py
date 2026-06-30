"""Summary generation — pure reporting logic, no cross-module imports."""


class Summary:
    def __init__(self, title: str) -> None:
        self.title = title
        self._rows: list[dict] = []

    def add_row(self, row: dict) -> None:
        self._rows.append(row)

    def render(self) -> str:
        return f"# {self.title}\n" + "\n".join(str(r) for r in self._rows)
