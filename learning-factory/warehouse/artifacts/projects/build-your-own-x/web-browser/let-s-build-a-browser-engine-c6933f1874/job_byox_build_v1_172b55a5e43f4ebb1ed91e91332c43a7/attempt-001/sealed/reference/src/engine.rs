use crate::css::parse_stylesheet;
use crate::dom::Document;
use crate::html::parse_document;
use crate::http::{build_get_request, parse_response};
use crate::layout::{layout_document, Layout};
use crate::paint::{paint, Canvas};
use crate::style::style_document;
use crate::url::Url;
use crate::{BrowserError, EngineLimits, Result};

pub trait Transport {
    fn exchange(&self, url: &Url, request: &[u8], max_response_bytes: usize) -> Result<Vec<u8>>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Page {
    pub url: Url,
    pub status: u16,
    pub request: Vec<u8>,
    pub document: Document,
    pub layout: Layout,
    pub canvas: Canvas,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BrowserEngine {
    pub limits: EngineLimits,
    pub viewport_width: usize,
}

impl BrowserEngine {
    pub fn new(limits: EngineLimits, viewport_width: usize) -> Self {
        Self {
            limits,
            viewport_width,
        }
    }

    pub fn load<T: Transport>(&self, input_url: &str, author_css: &str, transport: &T) -> Result<Page> {
        let url = Url::parse(input_url)?;
        let request = build_get_request(&url);
        let maximum_response_bytes = self
            .limits
            .max_header_bytes
            .checked_add(4)
            .and_then(|value| value.checked_add(self.limits.max_body_bytes))
            .ok_or_else(|| BrowserError::Network("response byte budget overflow".into()))?;
        let response_bytes = transport.exchange(&url, &request, maximum_response_bytes)?;
        if response_bytes.len() > maximum_response_bytes {
            return Err(BrowserError::Network(
                "transport returned more bytes than its budget".into(),
            ));
        }
        let response = parse_response(&response_bytes, &self.limits)?;
        if !(200..300).contains(&response.status) {
            return Err(BrowserError::Http(format!(
                "non-success response status {}",
                response.status
            )));
        }
        for (_, content_type) in response
            .headers
            .iter()
            .filter(|(name, _)| name == "content-type")
        {
            let media_type = content_type.split(';').next().unwrap_or("").trim();
            if !media_type.eq_ignore_ascii_case("text/html") {
                return Err(BrowserError::Http(
                    "response Content-Type is not text/html".into(),
                ));
            }
        }

        let document = parse_document(&response.body, &self.limits)?;
        let stylesheet = parse_stylesheet(author_css)?;
        let styled = style_document(&document, &stylesheet)?;
        let layout = layout_document(&styled, self.viewport_width)?;
        let canvas = paint(&layout)?;
        Ok(Page {
            url,
            status: response.status,
            request,
            document,
            layout,
            canvas,
        })
    }
}
