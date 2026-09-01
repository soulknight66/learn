use crate::url::Url;
use crate::{BrowserError, EngineLimits, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Response {
    pub version: String,
    pub status: u16,
    pub reason: String,
    pub headers: Vec<(String, String)>,
    pub body: String,
}

impl Response {
    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(candidate, _)| candidate.eq_ignore_ascii_case(name))
            .map(|(_, value)| value.as_str())
    }
}

pub fn build_get_request(url: &Url) -> Vec<u8> {
    let mut target = escape_visible(&url.path_and_query);
    if !target.starts_with('/') {
        target.insert(0, '/');
    }
    let host = escape_visible(&url.host);
    let authority = if url.port == 80 {
        host
    } else {
        format!("{host}:{}", url.port)
    };
    format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nUser-Agent: pocket-browser/1\r\nAccept: text/html\r\n\r\n",
        target, authority
    )
    .into_bytes()
}

fn escape_visible(input: &str) -> String {
    let mut output = String::with_capacity(input.len());
    for byte in input.bytes() {
        if (0x21..=0x7e).contains(&byte) {
            output.push(char::from(byte));
        } else {
            output.push_str(&format!("%{byte:02X}"));
        }
    }
    output
}

pub fn parse_response(bytes: &[u8], limits: &EngineLimits) -> Result<Response> {
    let searchable = bytes.len().min(limits.max_header_bytes.saturating_add(4));
    let delimiter = bytes[..searchable]
        .windows(4)
        .position(|window| window == b"\r\n\r\n")
        .ok_or_else(|| {
            if bytes.len() > limits.max_header_bytes {
                BrowserError::Http("header section exceeds its byte limit".into())
            } else {
                BrowserError::Http("missing CRLF/CRLF header boundary".into())
            }
        })?;
    if delimiter > limits.max_header_bytes {
        return Err(BrowserError::Http(
            "header section exceeds its byte limit".into(),
        ));
    }

    let head_bytes = &bytes[..delimiter];
    if !head_bytes.is_ascii() {
        return Err(BrowserError::Http("response head must be ASCII".into()));
    }
    let head = std::str::from_utf8(head_bytes)
        .map_err(|_| BrowserError::Http("response head is not valid ASCII".into()))?;
    let mut lines = head.split("\r\n");
    let status_line = lines
        .next()
        .ok_or_else(|| BrowserError::Http("missing status line".into()))?;
    let mut status_parts = status_line.splitn(3, ' ');
    let version = status_parts
        .next()
        .ok_or_else(|| BrowserError::Http("missing HTTP version".into()))?;
    let status_text = status_parts
        .next()
        .ok_or_else(|| BrowserError::Http("missing status code".into()))?;
    let reason = status_parts
        .next()
        .ok_or_else(|| BrowserError::Http("missing reason phrase".into()))?;
    if !matches!(version, "HTTP/1.0" | "HTTP/1.1") {
        return Err(BrowserError::Http("unsupported HTTP version".into()));
    }
    if status_text.len() != 3 || !status_text.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(BrowserError::Http("status code must be three digits".into()));
    }
    let status = status_text
        .parse::<u16>()
        .map_err(|_| BrowserError::Http("invalid status code".into()))?;

    let mut headers = Vec::new();
    let mut content_length: Option<usize> = None;
    for line in lines {
        if line.is_empty() {
            return Err(BrowserError::Http("unexpected empty header line".into()));
        }
        if line
            .as_bytes()
            .first()
            .is_some_and(|byte| matches!(*byte, b' ' | b'\t'))
        {
            return Err(BrowserError::Http("folded header lines are forbidden".into()));
        }
        let (name, raw_value) = line
            .split_once(':')
            .ok_or_else(|| BrowserError::Http("header is missing ':'".into()))?;
        if name.is_empty() || !name.bytes().all(is_token_byte) {
            return Err(BrowserError::Http("invalid header name".into()));
        }
        if raw_value
            .bytes()
            .any(|byte| byte.is_ascii_control() || byte == 0x7f)
        {
            return Err(BrowserError::Http("header value contains a control byte".into()));
        }
        let lower_name = name.to_ascii_lowercase();
        let value = raw_value.trim_matches(' ').to_string();
        if lower_name == "transfer-encoding" {
            return Err(BrowserError::Http(
                "transfer codings are outside this parser".into(),
            ));
        }
        if lower_name == "content-length" {
            if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(BrowserError::Http("invalid Content-Length".into()));
            }
            let parsed = value
                .parse::<usize>()
                .map_err(|_| BrowserError::Http("Content-Length is too large".into()))?;
            if content_length.is_some_and(|previous| previous != parsed) {
                return Err(BrowserError::Http(
                    "differing Content-Length values are ambiguous".into(),
                ));
            }
            content_length = Some(parsed);
        }
        headers.push((lower_name, value));
    }

    let body_start = delimiter
        .checked_add(4)
        .ok_or_else(|| BrowserError::Http("response offset overflow".into()))?;
    let available_body = &bytes[body_start..];
    let body_bytes = match content_length {
        Some(length) => {
            if length > limits.max_body_bytes {
                return Err(BrowserError::Http("body exceeds its byte limit".into()));
            }
            if available_body.len() != length {
                return Err(BrowserError::Http(
                    "body length does not equal Content-Length".into(),
                ));
            }
            available_body
        }
        None => {
            if available_body.len() > limits.max_body_bytes {
                return Err(BrowserError::Http("body exceeds its byte limit".into()));
            }
            available_body
        }
    };
    let body = std::str::from_utf8(body_bytes)
        .map_err(|_| BrowserError::Http("HTML body is not UTF-8".into()))?
        .to_string();

    Ok(Response {
        version: version.into(),
        status,
        reason: reason.into(),
        headers,
        body,
    })
}

fn is_token_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric()
        || matches!(
            byte,
            b'!' | b'#'
                | b'$'
                | b'%'
                | b'&'
                | b'\''
                | b'*'
                | b'+'
                | b'-'
                | b'.'
                | b'^'
                | b'_'
                | b'`'
                | b'|'
                | b'~'
        )
}
