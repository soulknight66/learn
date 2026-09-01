use crate::dom::Document;
use crate::layout::Layout;
use crate::paint::Canvas;
use crate::url::Url;
use crate::{EngineLimits, Result};

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
        let _ = (input_url, author_css, transport);
        todo!("milestone 6: connect all stages and enforce response policy")
    }
}
