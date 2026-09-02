# Cursor-position answer

`Position` describes the location of the next byte. Immediately after consuming
a newline, that byte is on the new line at one-based column 1, not column 0.
Change the newline assignment in `Advance` to `position.Column = 1`. Keep the
offset increment and line increment as written. The supplied regression then
distinguishes the fixed convention from both zero-based columns and a cursor
that still points at the newline.
