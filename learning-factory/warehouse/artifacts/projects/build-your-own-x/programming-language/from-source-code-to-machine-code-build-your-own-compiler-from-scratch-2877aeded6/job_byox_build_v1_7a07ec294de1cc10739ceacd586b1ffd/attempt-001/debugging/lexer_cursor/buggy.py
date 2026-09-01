def consume_newline(source, index, line, column):
    """Intentionally defective exercise snippet."""
    if source[index] == "\r":
        index += 1
    if source[index] == "\n":
        index += 1
    line += 1
    column += 1
    return index, line, column
