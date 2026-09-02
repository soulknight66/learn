'use strict';

function scan(source, maxSteps = source.length * 3 + 1) {
  const punctuation = new Set(['(', ')', ',', ';']);
  const tokens = [];
  let index = 0;
  let steps = 0;

  while (index < source.length) {
    steps += 1;
    if (steps > maxSteps) {
      const error = new Error(`scanner made no progress at offset ${index}`);
      error.code = 'SCANNER_STALLED';
      error.offset = index;
      throw error;
    }

    const character = source[index];
    if (character === ' ') {
      index += 1;
    } else if (punctuation.has(character)) {
      tokens.push({ kind: 'PUNCTUATION', value: character, offset: index });
    } else {
      const error = new Error(`unexpected character at offset ${index}`);
      error.code = 'UNEXPECTED_CHARACTER';
      error.offset = index;
      throw error;
    }
  }
  return tokens;
}

module.exports = { scan };
