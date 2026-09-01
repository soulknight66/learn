use crate::{BrowserError, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StyleSheet {
    pub rules: Vec<Rule>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Rule {
    pub selectors: Vec<Selector>,
    pub declarations: Vec<Declaration>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Selector {
    pub tag: Option<String>,
    pub id: Option<String>,
    pub classes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Declaration {
    pub name: String,
    pub value: String,
}

impl Selector {
    pub fn specificity(&self) -> (u16, u16, u16) {
        (
            if self.id.is_some() { 1 } else { 0 },
            self.classes.len().min(usize::from(u16::MAX)) as u16,
            if self.tag.is_some() { 1 } else { 0 },
        )
    }
}

pub fn parse_stylesheet(input: &str) -> Result<StyleSheet> {
    let source = strip_comments(input)?;
    if !source.is_ascii() {
        return Err(BrowserError::Css(
            "this CSS subset accepts ASCII syntax only".into(),
        ));
    }
    let mut rules = Vec::new();
    let mut position = 0;
    while position < source.len() {
        position = skip_whitespace(&source, position);
        if position == source.len() {
            break;
        }
        let open_relative = source[position..]
            .find('{')
            .ok_or_else(|| BrowserError::Css("rule is missing '{'".into()))?;
        let open = position + open_relative;
        if source[position..open].contains('}') {
            return Err(BrowserError::Css("unexpected '}' before rule body".into()));
        }
        let close_relative = source[open + 1..]
            .find('}')
            .ok_or_else(|| BrowserError::Css("rule is missing '}'".into()))?;
        let close = open + 1 + close_relative;
        if source[open + 1..close].contains('{') {
            return Err(BrowserError::Css("nested CSS blocks are unsupported".into()));
        }

        let selector_text = source[position..open].trim();
        let selectors = parse_selector_list(selector_text)?;
        let declarations = parse_declarations(&source[open + 1..close])?;
        rules.push(Rule {
            selectors,
            declarations,
        });
        position = close + 1;
    }
    Ok(StyleSheet { rules })
}

fn strip_comments(input: &str) -> Result<String> {
    let mut output = String::with_capacity(input.len());
    let mut remainder = input;
    loop {
        let Some(start) = remainder.find("/*") else {
            if remainder.contains("*/") {
                return Err(BrowserError::Css("orphan comment terminator".into()));
            }
            output.push_str(remainder);
            return Ok(output);
        };
        if remainder[..start].contains("*/") {
            return Err(BrowserError::Css("orphan comment terminator".into()));
        }
        output.push_str(&remainder[..start]);
        let after_start = &remainder[start + 2..];
        let end = after_start
            .find("*/")
            .ok_or_else(|| BrowserError::Css("unterminated comment".into()))?;
        remainder = &after_start[end + 2..];
    }
}

fn parse_selector_list(input: &str) -> Result<Vec<Selector>> {
    if input.is_empty() {
        return Err(BrowserError::Css("empty selector list".into()));
    }
    input.split(',').map(|part| parse_selector(part.trim())).collect()
}

fn parse_selector(input: &str) -> Result<Selector> {
    if input.is_empty() || input.bytes().any(|byte| byte.is_ascii_whitespace()) {
        return Err(BrowserError::Css(
            "compound selectors cannot be empty or contain whitespace".into(),
        ));
    }
    let bytes = input.as_bytes();
    let mut position = 0;
    let mut tag = None;
    let mut id = None;
    let mut classes = Vec::new();

    if bytes[position] == b'*' {
        position += 1;
    } else if bytes[position].is_ascii_alphabetic() {
        let end = consume_identifier(bytes, position);
        tag = Some(input[position..end].to_ascii_lowercase());
        position = end;
    }

    while position < bytes.len() {
        let prefix = bytes[position];
        if !matches!(prefix, b'#' | b'.') {
            return Err(BrowserError::Css("unsupported selector syntax".into()));
        }
        position += 1;
        let end = consume_identifier(bytes, position);
        if end == position {
            return Err(BrowserError::Css("empty selector component".into()));
        }
        let value = input[position..end].to_string();
        if prefix == b'#' {
            if id.replace(value).is_some() {
                return Err(BrowserError::Css(
                    "a compound selector may contain only one id".into(),
                ));
            }
        } else {
            classes.push(value);
        }
        position = end;
    }
    if tag.is_none() && id.is_none() && classes.is_empty() && input != "*" {
        return Err(BrowserError::Css("selector has no components".into()));
    }
    Ok(Selector { tag, id, classes })
}

fn consume_identifier(bytes: &[u8], mut position: usize) -> usize {
    while bytes.get(position).is_some_and(|byte| {
        byte.is_ascii_alphanumeric() || matches!(*byte, b'-' | b'_')
    }) {
        position += 1;
    }
    position
}

fn parse_declarations(input: &str) -> Result<Vec<Declaration>> {
    let mut declarations = Vec::new();
    for segment in input.split(';') {
        let declaration = segment.trim();
        if declaration.is_empty() {
            continue;
        }
        let (name, value) = declaration
            .split_once(':')
            .ok_or_else(|| BrowserError::Css("declaration is missing ':'".into()))?;
        let name = name.trim();
        let value = value.trim();
        if name.is_empty()
            || !name
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
        {
            return Err(BrowserError::Css("invalid property name".into()));
        }
        if value.is_empty() || value.contains(':') {
            return Err(BrowserError::Css("invalid property value".into()));
        }
        declarations.push(Declaration {
            name: name.to_ascii_lowercase(),
            value: value.to_string(),
        });
    }
    if declarations.is_empty() {
        return Err(BrowserError::Css("rule has no declarations".into()));
    }
    Ok(declarations)
}

fn skip_whitespace(input: &str, mut position: usize) -> usize {
    while input
        .as_bytes()
        .get(position)
        .is_some_and(|byte| byte.is_ascii_whitespace())
    {
        position += 1;
    }
    position
}
