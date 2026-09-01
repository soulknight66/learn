use std::collections::BTreeMap;

use crate::dom::{Document, Node};
use crate::{BrowserError, EngineLimits, Result};

pub fn parse_document(input: &str, limits: &EngineLimits) -> Result<Document> {
    let mut parser = Parser {
        input,
        position: 0,
        limits,
        node_count: 0,
    };
    let children = parser.parse_nodes(None, 0)?;
    Ok(Document { children })
}

struct Parser<'a> {
    input: &'a str,
    position: usize,
    limits: &'a EngineLimits,
    node_count: usize,
}

impl Parser<'_> {
    fn parse_nodes(&mut self, expected_close: Option<&str>, depth: usize) -> Result<Vec<Node>> {
        let mut nodes = Vec::new();
        while !self.is_eof() {
            if self.remaining().starts_with("</") {
                let closing = self.parse_closing_tag()?;
                return match expected_close {
                    Some(expected) if closing == expected => Ok(nodes),
                    Some(expected) => Err(BrowserError::Html(format!(
                        "expected </{expected}> but found </{closing}>"
                    ))),
                    None => Err(BrowserError::Html(format!(
                        "unexpected top-level closing tag </{closing}>"
                    ))),
                };
            }
            if self.remaining().starts_with("<!--") {
                self.parse_comment()?;
            } else if self.starts_with_doctype() {
                self.parse_doctype()?;
            } else if self.remaining().starts_with('<') {
                nodes.push(self.parse_element(depth)?);
            } else {
                let text = self.parse_text()?;
                if !text.is_empty() {
                    self.charge_node()?;
                    nodes.push(Node::text(text));
                }
            }
        }

        if let Some(expected) = expected_close {
            Err(BrowserError::Html(format!(
                "input ended before </{expected}>"
            )))
        } else {
            Ok(nodes)
        }
    }

    fn parse_element(&mut self, depth: usize) -> Result<Node> {
        if depth >= self.limits.max_dom_depth {
            return Err(BrowserError::Html("DOM depth limit exceeded".into()));
        }
        self.expect_byte(b'<')?;
        let tag_name = self.parse_name("tag")?;
        let mut attributes = BTreeMap::new();
        let self_closing;

        loop {
            self.skip_ascii_whitespace();
            match self.peek_byte() {
                Some(b'>') => {
                    self.position += 1;
                    self_closing = false;
                    break;
                }
                Some(b'/') => {
                    self.position += 1;
                    self.expect_byte(b'>')?;
                    self_closing = true;
                    break;
                }
                Some(_) => {
                    let name = self.parse_name("attribute")?;
                    if attributes.contains_key(&name) {
                        return Err(BrowserError::Html(format!(
                            "duplicate attribute {name}"
                        )));
                    }
                    self.skip_ascii_whitespace();
                    self.expect_byte(b'=')?;
                    self.skip_ascii_whitespace();
                    let quote = self.peek_byte().ok_or_else(|| {
                        BrowserError::Html("missing quoted attribute value".into())
                    })?;
                    if !matches!(quote, b'\'' | b'"') {
                        return Err(BrowserError::Html(
                            "attribute values must be quoted".into(),
                        ));
                    }
                    self.position += 1;
                    let value_start = self.position;
                    while self.peek_byte().is_some_and(|byte| byte != quote) {
                        self.position += 1;
                    }
                    if self.peek_byte() != Some(quote) {
                        return Err(BrowserError::Html(
                            "unterminated attribute value".into(),
                        ));
                    }
                    let raw_value = &self.input[value_start..self.position];
                    if raw_value
                        .bytes()
                        .any(|byte| byte.is_ascii_control() || byte == b'<')
                    {
                        return Err(BrowserError::Html(
                            "attribute value contains a forbidden byte".into(),
                        ));
                    }
                    let value = decode_entities(raw_value)?;
                    self.position += 1;
                    attributes.insert(name, value);
                }
                None => {
                    return Err(BrowserError::Html(
                        "input ended inside a start tag".into(),
                    ));
                }
            }
        }

        self.charge_node()?;
        let is_void = matches!(
            tag_name.as_str(),
            "br" | "img" | "meta" | "link" | "input" | "hr"
        );
        let children = if self_closing || is_void {
            Vec::new()
        } else {
            self.parse_nodes(Some(&tag_name), depth + 1)?
        };
        Ok(Node::element(tag_name, attributes, children))
    }

    fn parse_closing_tag(&mut self) -> Result<String> {
        self.position += 2;
        let name = self.parse_name("closing tag")?;
        self.skip_ascii_whitespace();
        self.expect_byte(b'>')?;
        Ok(name)
    }

    fn parse_comment(&mut self) -> Result<()> {
        self.position += 4;
        let relative_end = self.remaining().find("-->").ok_or_else(|| {
            BrowserError::Html("unterminated HTML comment".into())
        })?;
        self.position = self
            .position
            .checked_add(relative_end + 3)
            .ok_or_else(|| BrowserError::Html("comment offset overflow".into()))?;
        Ok(())
    }

    fn starts_with_doctype(&self) -> bool {
        const PREFIX: &str = "<!doctype";
        let Some(candidate) = self
            .input
            .get(self.position..self.position.saturating_add(PREFIX.len()))
        else {
            return false;
        };
        if !candidate.eq_ignore_ascii_case(PREFIX) {
            return false;
        }
        matches!(
            self.input.as_bytes().get(self.position + PREFIX.len()),
            Some(b'>') | Some(b' ') | Some(b'\t') | Some(b'\r') | Some(b'\n')
        )
    }

    fn parse_doctype(&mut self) -> Result<()> {
        let relative_end = self
            .remaining()
            .find('>')
            .ok_or_else(|| BrowserError::Html("unterminated doctype".into()))?;
        self.position = self
            .position
            .checked_add(relative_end + 1)
            .ok_or_else(|| BrowserError::Html("doctype offset overflow".into()))?;
        Ok(())
    }

    fn parse_text(&mut self) -> Result<String> {
        let relative_end = self.remaining().find('<').unwrap_or(self.remaining().len());
        let end = self
            .position
            .checked_add(relative_end)
            .ok_or_else(|| BrowserError::Html("text offset overflow".into()))?;
        let decoded = decode_entities(&self.input[self.position..end])?;
        self.position = end;
        Ok(decoded)
    }

    fn parse_name(&mut self, context: &str) -> Result<String> {
        let start = self.position;
        let first = self
            .peek_byte()
            .ok_or_else(|| BrowserError::Html(format!("missing {context} name")))?;
        if !first.is_ascii_alphabetic() {
            return Err(BrowserError::Html(format!(
                "{context} name must begin with an ASCII letter"
            )));
        }
        self.position += 1;
        while self.peek_byte().is_some_and(|byte| {
            byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_')
        }) {
            self.position += 1;
        }
        Ok(self.input[start..self.position].to_ascii_lowercase())
    }

    fn charge_node(&mut self) -> Result<()> {
        self.node_count = self
            .node_count
            .checked_add(1)
            .ok_or_else(|| BrowserError::Html("node counter overflow".into()))?;
        if self.node_count > self.limits.max_nodes {
            return Err(BrowserError::Html("DOM node limit exceeded".into()));
        }
        Ok(())
    }

    fn expect_byte(&mut self, expected: u8) -> Result<()> {
        if self.peek_byte() != Some(expected) {
            return Err(BrowserError::Html(format!(
                "expected byte {:?}",
                char::from(expected)
            )));
        }
        self.position += 1;
        Ok(())
    }

    fn skip_ascii_whitespace(&mut self) {
        while self
            .peek_byte()
            .is_some_and(|byte| byte.is_ascii_whitespace())
        {
            self.position += 1;
        }
    }

    fn peek_byte(&self) -> Option<u8> {
        self.input.as_bytes().get(self.position).copied()
    }

    fn remaining(&self) -> &str {
        &self.input[self.position..]
    }

    fn is_eof(&self) -> bool {
        self.position == self.input.len()
    }
}

fn decode_entities(input: &str) -> Result<String> {
    let mut output = String::with_capacity(input.len());
    let mut position = 0;
    while let Some(relative_ampersand) = input[position..].find('&') {
        let ampersand = position + relative_ampersand;
        output.push_str(&input[position..ampersand]);
        let after_ampersand = ampersand + 1;
        let relative_semicolon = input[after_ampersand..]
            .find(';')
            .ok_or_else(|| BrowserError::Html("unterminated character entity".into()))?;
        let semicolon = after_ampersand + relative_semicolon;
        let entity = &input[after_ampersand..semicolon];
        let decoded = match entity {
            "amp" => '&',
            "lt" => '<',
            "gt" => '>',
            "quot" => '"',
            "#39" => '\'',
            _ => {
                return Err(BrowserError::Html(format!(
                    "unsupported character entity &{entity};"
                )));
            }
        };
        output.push(decoded);
        position = semicolon + 1;
    }
    output.push_str(&input[position..]);
    Ok(output)
}
