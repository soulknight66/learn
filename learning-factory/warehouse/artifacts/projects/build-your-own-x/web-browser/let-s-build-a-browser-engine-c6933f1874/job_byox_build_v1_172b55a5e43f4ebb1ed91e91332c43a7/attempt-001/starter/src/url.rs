use crate::Result;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Url {
    pub scheme: String,
    pub host: String,
    pub port: u16,
    pub path_and_query: String,
}

impl Url {
    pub fn parse(input: &str) -> Result<Self> {
        let _ = input;
        todo!("milestone 1: parse and validate an HTTP URL")
    }

    pub fn authority(&self) -> String {
        todo!("milestone 1: format the Host authority")
    }
}
