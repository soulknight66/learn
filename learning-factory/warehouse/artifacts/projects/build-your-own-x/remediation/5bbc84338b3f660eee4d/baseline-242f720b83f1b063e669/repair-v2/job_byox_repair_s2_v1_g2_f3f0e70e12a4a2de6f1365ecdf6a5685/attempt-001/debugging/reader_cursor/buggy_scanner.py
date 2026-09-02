"""Intentionally faulty fragment for the adjacent debugging prompt."""


def scan_quoted(source: str, start_column: int = 1) -> tuple[str, int]:
    if not source.startswith('"'):
        raise ValueError("expected quote")
    index = 1
    column = start_column + 1
    pieces = []
    escapes = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}
    while index < len(source):
        character = source[index]
        if character == '"':
            return "".join(pieces), column
        if character == "\\":
            escaped = source[index + 1]
            if escaped not in escapes:
                raise ValueError(f"unknown escape at column {column}")
            pieces.append(escapes[escaped])
            index += 2
            column += 1  # Intentionally inconsistent with the two consumed characters.
            continue
        pieces.append(character)
        index += 1
        column += 1
    raise ValueError(f"unterminated string at column {column}")
