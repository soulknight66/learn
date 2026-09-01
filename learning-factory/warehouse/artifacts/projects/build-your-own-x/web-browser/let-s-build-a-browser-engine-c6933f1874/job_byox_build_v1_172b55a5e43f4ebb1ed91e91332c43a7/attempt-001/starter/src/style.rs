use std::collections::BTreeMap;

use crate::css::{Selector, StyleSheet};
use crate::dom::{Document, ElementData, Node};
use crate::Result;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Display {
    Block,
    Inline,
    None,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Color {
    pub r: u8,
    pub g: u8,
    pub b: u8,
}

impl Color {
    pub const BLACK: Self = Self { r: 0, g: 0, b: 0 };
    pub const WHITE: Self = Self {
        r: 255,
        g: 255,
        b: 255,
    };
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StyledNode {
    pub node: Node,
    pub properties: BTreeMap<String, String>,
    pub display: Display,
    pub color: Color,
    pub background: Option<Color>,
    pub children: Vec<StyledNode>,
}

pub fn selector_matches(selector: &Selector, element: &ElementData) -> bool {
    let _ = (selector, element);
    todo!("milestone 4: match compound selectors")
}

pub fn style_document(document: &Document, sheet: &StyleSheet) -> Result<Vec<StyledNode>> {
    let _ = (document, sheet);
    todo!("milestone 4: cascade declarations and inherit color")
}
