PYTHON ?= python3
SHELL_UNDER_TEST ?= $(abspath ../reference/byosh)

.PHONY: test

test:
	@test -x "$(SHELL_UNDER_TEST)" || { \
		echo "missing executable: $(SHELL_UNDER_TEST)" >&2; exit 1; \
	}
	SHELL_UNDER_TEST="$(SHELL_UNDER_TEST)" $(PYTHON) -m unittest -v test_shell.py
