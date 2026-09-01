use crate::{BrowserError, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Url {
    pub scheme: String,
    pub host: String,
    pub port: u16,
    pub path_and_query: String,
}

impl Url {
    pub fn parse(input: &str) -> Result<Self> {
        if input.is_empty()
            || !input.is_ascii()
            || input
                .bytes()
                .any(|byte| byte.is_ascii_control() || byte.is_ascii_whitespace())
        {
            return Err(BrowserError::Url(
                "URL must be non-empty ASCII without whitespace or controls".into(),
            ));
        }

        let (scheme, remainder) = input
            .split_once("://")
            .ok_or_else(|| BrowserError::Url("missing scheme delimiter".into()))?;
        if !scheme.eq_ignore_ascii_case("http") {
            return Err(BrowserError::Url("only the http scheme is supported".into()));
        }
        if remainder.contains('#') {
            return Err(BrowserError::Url("fragments are not request targets".into()));
        }

        let boundary = remainder
            .char_indices()
            .find_map(|(index, character)| matches!(character, '/' | '?').then_some(index))
            .unwrap_or(remainder.len());
        let authority = &remainder[..boundary];
        let suffix = &remainder[boundary..];

        if authority.is_empty() || authority.contains('@') {
            return Err(BrowserError::Url(
                "authority must contain a host and no credentials".into(),
            ));
        }
        if authority.starts_with('[') || authority.matches(':').count() > 1 {
            return Err(BrowserError::Url(
                "IPv6 literals are outside this URL subset".into(),
            ));
        }

        let (host_text, port) = match authority.split_once(':') {
            Some((host, port_text)) => {
                if port_text.is_empty() || !port_text.bytes().all(|byte| byte.is_ascii_digit()) {
                    return Err(BrowserError::Url("port must contain decimal digits".into()));
                }
                let port = port_text
                    .parse::<u16>()
                    .map_err(|_| BrowserError::Url("port is outside 1..=65535".into()))?;
                if port == 0 {
                    return Err(BrowserError::Url("port is outside 1..=65535".into()));
                }
                (host, port)
            }
            None => (authority, 80),
        };
        validate_host(host_text)?;

        let path_and_query = if suffix.is_empty() {
            "/".to_string()
        } else if suffix.starts_with('?') {
            format!("/{suffix}")
        } else {
            suffix.to_string()
        };

        Ok(Self {
            scheme: "http".into(),
            host: host_text.to_ascii_lowercase(),
            port,
            path_and_query,
        })
    }

    pub fn authority(&self) -> String {
        if self.port == 80 {
            self.host.clone()
        } else {
            format!("{}:{}", self.host, self.port)
        }
    }
}

fn validate_host(host: &str) -> Result<()> {
    if host.is_empty() || host.len() > 253 {
        return Err(BrowserError::Url("host length is invalid".into()));
    }
    if !host
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-'))
    {
        return Err(BrowserError::Url("host contains an unsupported byte".into()));
    }
    for label in host.split('.') {
        if label.is_empty()
            || label.len() > 63
            || label.starts_with('-')
            || label.ends_with('-')
        {
            return Err(BrowserError::Url("host contains an invalid label".into()));
        }
    }
    Ok(())
}
