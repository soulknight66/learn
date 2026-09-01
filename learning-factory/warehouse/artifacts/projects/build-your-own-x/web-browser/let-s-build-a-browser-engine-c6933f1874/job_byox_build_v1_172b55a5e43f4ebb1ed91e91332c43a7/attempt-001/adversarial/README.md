# Adversarial reveal: hostile inputs

Use these cases after the visible suite passes. Add tests before changing code.

1. Put CR, LF, NUL, a space, and non-ASCII bytes at every URL component boundary. Confirm no input can create a second request line or header.
2. Place CRLF/CRLF exactly at, one byte before, and one byte after the header limit.
3. Combine duplicate Content-Length values, comma-separated lengths, Transfer-Encoding, truncated bodies, and trailing bytes.
4. Generate deeply nested empty elements separately from a wide forest of text nodes. Each should trip only its relevant budget.
5. Try unknown, unterminated, and adjacent entities in text and attributes.
6. Create selector ties, multiple matching selectors in one rule, duplicate declarations, and invalid values on selectors that match no node.
7. Use dimensions near `usize::MAX`, decorations wider than the viewport, empty text, and a one-column viewport.
8. Construct rectangles that touch each canvas boundary and child backgrounds that completely cover their parent.
9. Make a transport return one byte over its supplied budget and count calls on every failure path.

Expected outcomes are intentionally withheld from this reveal; derive them from `REQUIREMENTS.md` before consulting sealed review material.
