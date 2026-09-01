use crate::url::Url;
use crate::{EngineLimits, Result};

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
        let _ = name;
        todo!("milestone 2: case-insensitive header lookup")
    }
}

pub fn build_get_request(url: &Url) -> Vec<u8> {
    let _ = url;
    todo!("milestone 1: serialize a fixed HTTP/1.1 GET")
}

pub fn parse_response(bytes: &[u8], limits: &EngineLimits) -> Result<Response> {
    let _ = (bytes, limits);
    todo!("milestone 2: parse a bounded, unambiguous response")
}
