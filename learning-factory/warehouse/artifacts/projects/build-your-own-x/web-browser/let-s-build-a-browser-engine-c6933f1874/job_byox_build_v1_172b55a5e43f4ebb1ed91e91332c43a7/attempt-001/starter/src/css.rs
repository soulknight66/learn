use crate::Result;

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
        todo!("milestone 4: calculate selector specificity")
    }
}

pub fn parse_stylesheet(input: &str) -> Result<StyleSheet> {
    let _ = input;
    todo!("milestone 4: parse flat CSS rules")
}
