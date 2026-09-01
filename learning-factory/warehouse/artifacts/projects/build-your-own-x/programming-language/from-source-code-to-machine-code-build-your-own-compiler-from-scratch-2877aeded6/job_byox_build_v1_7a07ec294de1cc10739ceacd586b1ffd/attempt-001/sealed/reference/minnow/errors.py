"""Stable reference error categories."""


class MiniError(Exception):
    def __init__(self, code, message, *, line=None, column=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.line = line
        self.column = column

    def __str__(self):
        if self.line is not None and self.column is not None:
            return f"{self.code} at {self.line}:{self.column}: {self.message}"
        return f"{self.code}: {self.message}"


class LexError(MiniError):
    def __init__(self, message, *, line, column, code="LEX001"):
        super().__init__(code, message, line=line, column=column)


class ParseError(MiniError):
    def __init__(self, message, *, line, column, code="PARSE001"):
        super().__init__(code, message, line=line, column=column)


class SemanticError(MiniError):
    def __init__(self, message, *, line, column, code="SEM001"):
        super().__init__(code, message, line=line, column=column)


class FormatError(MiniError):
    def __init__(self, message, *, code="FORMAT001"):
        super().__init__(code, message)


class RuntimeFault(MiniError):
    def __init__(self, message, *, code="RUNTIME001"):
        super().__init__(code, message)


class StepLimitExceeded(MiniError):
    def __init__(self, message="instruction step limit exceeded", *, code="LIMIT001"):
        super().__init__(code, message)
