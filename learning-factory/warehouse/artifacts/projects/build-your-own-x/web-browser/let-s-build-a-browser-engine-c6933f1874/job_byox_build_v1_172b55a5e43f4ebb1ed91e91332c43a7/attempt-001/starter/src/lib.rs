#![forbid(unsafe_code)]

use std::fmt;

pub mod css;
pub mod dom;
pub mod engine;
pub mod html;
pub mod http;
pub mod layout;
pub mod paint;
pub mod style;
pub mod url;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BrowserError {
    Url(String),
    Http(String),
    Html(String),
    Css(String),
    Layout(String),
    Network(String),
}

impl fmt::Display for BrowserError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let (stage, message) = match self {
            Self::Url(message) => ("URL", message),
            Self::Http(message) => ("HTTP", message),
            Self::Html(message) => ("HTML", message),
            Self::Css(message) => ("CSS", message),
            Self::Layout(message) => ("layout", message),
            Self::Network(message) => ("network", message),
        };
        write!(f, "{stage} error: {message}")
    }
}

impl std::error::Error for BrowserError {}

pub type Result<T> = std::result::Result<T, BrowserError>;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EngineLimits {
    pub max_header_bytes: usize,
    pub max_body_bytes: usize,
    pub max_dom_depth: usize,
    pub max_nodes: usize,
}

impl Default for EngineLimits {
    fn default() -> Self {
        Self {
            max_header_bytes: 8 * 1024,
            max_body_bytes: 1024 * 1024,
            max_dom_depth: 64,
            max_nodes: 10_000,
        }
    }
}
