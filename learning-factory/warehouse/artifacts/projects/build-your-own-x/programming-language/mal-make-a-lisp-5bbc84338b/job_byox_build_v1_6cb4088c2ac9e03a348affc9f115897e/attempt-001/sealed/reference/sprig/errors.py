"""Stable, language-level diagnostics."""


class LanguageError(Exception):
    def __init__(self, code, message, line=None, column=None):
        self.code = code
        self.message = message
        self.line = line
        self.column = column
        Exception.__init__(self, message)

    def __str__(self):
        location = ""
        if self.line is not None and self.column is not None:
            location = " at {0}:{1}".format(self.line, self.column)
        return "{0}{1}: {2}".format(self.code, location, self.message)
