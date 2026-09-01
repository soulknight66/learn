use crate::layout::Layout;
use crate::style::Color;
use crate::Result;

pub const MAX_CANVAS_PIXELS: usize = 16_777_216;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Canvas {
    pub width: usize,
    pub height: usize,
    pub pixels: Vec<Color>,
}

impl Canvas {
    pub fn pixel(&self, x: usize, y: usize) -> Option<Color> {
        if x >= self.width || y >= self.height {
            return None;
        }
        self.pixels.get(y.checked_mul(self.width)?.checked_add(x)?).copied()
    }
}

pub fn paint(layout: &Layout) -> Result<Canvas> {
    let _ = layout;
    todo!("milestone 5: paint clipped backgrounds in tree order")
}
