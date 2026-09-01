use crate::style::{Color, StyledNode};
use crate::Result;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Rect {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LayoutBox {
    pub rect: Rect,
    pub background: Option<Color>,
    pub color: Color,
    pub text_lines: Vec<String>,
    pub children: Vec<LayoutBox>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Layout {
    pub width: usize,
    pub height: usize,
    pub boxes: Vec<LayoutBox>,
}

pub fn layout_document(nodes: &[StyledNode], viewport_width: usize) -> Result<Layout> {
    let _ = (nodes, viewport_width);
    todo!("milestone 5: perform block flow and text wrapping")
}
