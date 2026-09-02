"""Review candidate; intentionally does not implement Pebble's truth rule."""


def choose_branch(value, consequent, alternative):
    return consequent if value else alternative
