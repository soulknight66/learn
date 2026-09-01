use crate::layout::{Layout, LayoutBox};
use crate::style::Color;
use crate::{BrowserError, Result};

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
    let pixel_count = layout
        .width
        .checked_mul(layout.height)
        .ok_or_else(|| BrowserError::Layout("canvas dimensions overflow".into()))?;
    if pixel_count > MAX_CANVAS_PIXELS {
        return Err(BrowserError::Layout(
            "canvas exceeds the pixel allocation limit".into(),
        ));
    }
    let mut pixels = Vec::new();
    pixels
        .try_reserve_exact(pixel_count)
        .map_err(|_| BrowserError::Layout("canvas allocation failed".into()))?;
    pixels.resize(pixel_count, Color::WHITE);
    let mut canvas = Canvas {
        width: layout.width,
        height: layout.height,
        pixels,
    };
    for layout_box in &layout.boxes {
        paint_box(layout_box, &mut canvas);
    }
    Ok(canvas)
}

fn paint_box(layout_box: &LayoutBox, canvas: &mut Canvas) {
    if let Some(color) = layout_box.background {
        let x_end = layout_box
            .rect
            .x
            .saturating_add(layout_box.rect.width)
            .min(canvas.width);
        let y_end = layout_box
            .rect
            .y
            .saturating_add(layout_box.rect.height)
            .min(canvas.height);
        for y in layout_box.rect.y.min(canvas.height)..y_end {
            for x in layout_box.rect.x.min(canvas.width)..x_end {
                if let Some(pixel) = canvas
                    .pixels
                    .get_mut(y.saturating_mul(canvas.width).saturating_add(x))
                {
                    *pixel = color;
                }
            }
        }
    }
    for child in &layout_box.children {
        paint_box(child, canvas);
    }
}
