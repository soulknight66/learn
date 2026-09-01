use std::collections::BTreeMap;

use crate::css::{Selector, StyleSheet};
use crate::dom::{Document, ElementData, Node, NodeType};
use crate::{BrowserError, Result};

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
    if selector
        .tag
        .as_ref()
        .is_some_and(|tag| tag != &element.tag_name)
    {
        return false;
    }
    if selector.id.as_ref().is_some_and(|id| {
        element.attributes.get("id").map(String::as_str) != Some(id.as_str())
    }) {
        return false;
    }
    let element_classes = element
        .attributes
        .get("class")
        .map(|value| value.split_ascii_whitespace().collect::<Vec<_>>())
        .unwrap_or_default();
    selector
        .classes
        .iter()
        .all(|class| element_classes.contains(&class.as_str()))
}

pub fn style_document(document: &Document, sheet: &StyleSheet) -> Result<Vec<StyledNode>> {
    validate_sheet(sheet)?;
    document
        .children
        .iter()
        .map(|node| style_node(node, sheet, Color::BLACK))
        .collect()
}

fn style_node(node: &Node, sheet: &StyleSheet, inherited_color: Color) -> Result<StyledNode> {
    let NodeType::Element(element) = &node.node_type else {
        return Ok(StyledNode {
            node: node.clone(),
            properties: BTreeMap::new(),
            display: Display::Inline,
            color: inherited_color,
            background: None,
            children: Vec::new(),
        });
    };

    type Specificity = (u16, u16, u16);
    let mut selected: BTreeMap<String, (Specificity, usize, String)> = BTreeMap::new();
    let mut source_order = 0usize;
    for rule in &sheet.rules {
        let matching_specificity = rule
            .selectors
            .iter()
            .filter(|selector| selector_matches(selector, element))
            .map(Selector::specificity)
            .max();
        for declaration in &rule.declarations {
            if let Some(specificity) = matching_specificity {
                let should_replace = selected
                    .get(&declaration.name)
                    .map(|(old_specificity, old_order, _)| {
                        (specificity, source_order) >= (*old_specificity, *old_order)
                    })
                    .unwrap_or(true);
                if should_replace {
                    selected.insert(
                        declaration.name.clone(),
                        (specificity, source_order, declaration.value.clone()),
                    );
                }
            }
            source_order = source_order.saturating_add(1);
        }
    }
    let properties = selected
        .into_iter()
        .map(|(name, (_, _, value))| (name, value))
        .collect::<BTreeMap<_, _>>();

    let display = match properties.get("display").map(String::as_str) {
        Some("block") => Display::Block,
        Some("inline") => Display::Inline,
        Some("none") => Display::None,
        Some(_) => unreachable!("validated before styling"),
        None => user_agent_display(&element.tag_name),
    };
    let color = properties
        .get("color")
        .map(|value| parse_color(value))
        .transpose()?
        .unwrap_or(inherited_color);
    let background = match properties.get("background").map(String::as_str) {
        Some("transparent") | None => None,
        Some(value) => Some(parse_color(value)?),
    };
    let children = node
        .children
        .iter()
        .map(|child| style_node(child, sheet, color))
        .collect::<Result<Vec<_>>>()?;

    Ok(StyledNode {
        node: node.clone(),
        properties,
        display,
        color,
        background,
        children,
    })
}

fn validate_sheet(sheet: &StyleSheet) -> Result<()> {
    for declaration in sheet.rules.iter().flat_map(|rule| &rule.declarations) {
        match declaration.name.as_str() {
            "display" => {
                if !matches!(declaration.value.as_str(), "block" | "inline" | "none") {
                    return Err(BrowserError::Css("invalid display value".into()));
                }
            }
            "color" => {
                parse_color(&declaration.value)?;
            }
            "background" => {
                if declaration.value != "transparent" {
                    parse_color(&declaration.value)?;
                }
            }
            "width" | "height" | "margin" | "padding" => {
                parse_pixels(&declaration.value)?;
            }
            _ => {}
        }
    }
    Ok(())
}

fn user_agent_display(tag: &str) -> Display {
    match tag {
        "head" | "style" | "script" => Display::None,
        "html" | "body" | "main" | "div" | "p" | "h1" | "h2" | "h3" | "ul"
        | "ol" | "li" | "section" | "article" | "header" | "footer" | "nav" => {
            Display::Block
        }
        _ => Display::Inline,
    }
}

fn parse_color(value: &str) -> Result<Color> {
    let named = match value {
        "black" => Some(Color::BLACK),
        "white" => Some(Color::WHITE),
        "red" => Some(Color { r: 255, g: 0, b: 0 }),
        "green" => Some(Color { r: 0, g: 128, b: 0 }),
        "blue" => Some(Color { r: 0, g: 0, b: 255 }),
        _ => None,
    };
    if let Some(color) = named {
        return Ok(color);
    }
    if value.len() != 7 || !value.starts_with('#') {
        return Err(BrowserError::Css(format!(
            "unsupported color value {value:?}"
        )));
    }
    let component = |range: std::ops::Range<usize>| {
        u8::from_str_radix(&value[range], 16)
            .map_err(|_| BrowserError::Css(format!("invalid hex color {value:?}")))
    };
    Ok(Color {
        r: component(1..3)?,
        g: component(3..5)?,
        b: component(5..7)?,
    })
}

fn parse_pixels(value: &str) -> Result<usize> {
    let number = value
        .strip_suffix("px")
        .ok_or_else(|| BrowserError::Css("dimension must end in px".into()))?;
    if number.is_empty() || !number.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(BrowserError::Css(
            "dimension must be a non-negative integer".into(),
        ));
    }
    number
        .parse::<usize>()
        .map_err(|_| BrowserError::Css("dimension is too large".into()))
}
