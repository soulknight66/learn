use crate::dom::NodeType;
use crate::style::{Color, Display, StyledNode};
use crate::{BrowserError, Result};

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
    if viewport_width == 0 {
        return Err(BrowserError::Layout(
            "viewport width must be greater than zero".into(),
        ));
    }
    let mut boxes = Vec::new();
    let mut cursor_y = 0usize;
    for node in nodes {
        if let Some((layout_box, occupied_height)) =
            layout_node(node, 0, cursor_y, viewport_width)?
        {
            cursor_y = checked_add(cursor_y, occupied_height, "document height")?;
            boxes.push(layout_box);
        }
    }
    Ok(Layout {
        width: viewport_width,
        height: cursor_y,
        boxes,
    })
}

fn layout_node(
    node: &StyledNode,
    x: usize,
    y: usize,
    available_width: usize,
) -> Result<Option<(LayoutBox, usize)>> {
    if node.display == Display::None {
        return Ok(None);
    }
    if let NodeType::Text(value) = &node.node.node_type {
        let collapsed = value
            .split_ascii_whitespace()
            .collect::<Vec<_>>()
            .join(" ");
        if collapsed.is_empty() {
            return Ok(None);
        }
        if available_width == 0 {
            return Err(BrowserError::Layout("no width available for text".into()));
        }
        let text_lines = wrap_text(&collapsed, available_width);
        let height = text_lines.len();
        return Ok(Some((
            LayoutBox {
                rect: Rect {
                    x,
                    y,
                    width: available_width,
                    height,
                },
                background: None,
                color: node.color,
                text_lines,
                children: Vec::new(),
            },
            height,
        )));
    }

    let margin = pixel_property(node, "margin")?.unwrap_or(0);
    let padding = pixel_property(node, "padding")?.unwrap_or(0);
    let double_margin = checked_mul(margin, 2, "horizontal margin")?;
    let double_padding = checked_mul(padding, 2, "horizontal padding")?;
    let decorations = checked_add(double_margin, double_padding, "box decorations")?;
    if decorations > available_width {
        return Err(BrowserError::Layout(
            "margin and padding exceed available width".into(),
        ));
    }
    let maximum_content_width = available_width - decorations;
    let content_width = pixel_property(node, "width")?
        .map(|width| width.min(maximum_content_width))
        .unwrap_or(maximum_content_width);
    let rect_x = checked_add(x, margin, "box x coordinate")?;
    let rect_y = checked_add(y, margin, "box y coordinate")?;
    let child_x = checked_add(rect_x, padding, "child x coordinate")?;
    let mut child_y = checked_add(rect_y, padding, "child y coordinate")?;
    let mut content_height = 0usize;
    let mut children = Vec::new();

    for child in &node.children {
        if let Some((child_box, child_occupied)) =
            layout_node(child, child_x, child_y, content_width)?
        {
            child_y = checked_add(child_y, child_occupied, "child flow position")?;
            content_height = checked_add(content_height, child_occupied, "content height")?;
            children.push(child_box);
        }
    }
    if let Some(minimum_height) = pixel_property(node, "height")? {
        content_height = content_height.max(minimum_height);
    }

    let rect_width = checked_add(content_width, double_padding, "box width")?;
    let rect_height = checked_add(content_height, double_padding, "box height")?;
    let occupied_height = checked_add(rect_height, double_margin, "occupied box height")?;
    Ok(Some((
        LayoutBox {
            rect: Rect {
                x: rect_x,
                y: rect_y,
                width: rect_width,
                height: rect_height,
            },
            background: node.background,
            color: node.color,
            text_lines: Vec::new(),
            children,
        },
        occupied_height,
    )))
}

fn pixel_property(node: &StyledNode, name: &str) -> Result<Option<usize>> {
    node.properties
        .get(name)
        .map(|value| {
            let number = value.strip_suffix("px").ok_or_else(|| {
                BrowserError::Layout(format!("{name} must use px units"))
            })?;
            number.parse::<usize>().map_err(|_| {
                BrowserError::Layout(format!("{name} is outside the supported integer range"))
            })
        })
        .transpose()
}

fn wrap_text(text: &str, width: usize) -> Vec<String> {
    let mut lines = Vec::new();
    let mut current = String::new();
    let mut current_width = 0usize;

    for word in text.split(' ') {
        let characters = word.chars().collect::<Vec<_>>();
        if characters.len() <= width {
            if current.is_empty() {
                current.push_str(word);
                current_width = characters.len();
            } else if current_width + 1 + characters.len() <= width {
                current.push(' ');
                current.push_str(word);
                current_width += 1 + characters.len();
            } else {
                lines.push(std::mem::take(&mut current));
                current.push_str(word);
                current_width = characters.len();
            }
            continue;
        }

        if !current.is_empty() {
            lines.push(std::mem::take(&mut current));
            current_width = 0;
        }
        let mut chunks = characters.chunks(width).peekable();
        while let Some(chunk) = chunks.next() {
            let chunk_text = chunk.iter().copied().collect::<String>();
            if chunks.peek().is_some() {
                lines.push(chunk_text);
            } else {
                current_width = chunk.len();
                current = chunk_text;
            }
        }
    }
    if !current.is_empty() {
        lines.push(current);
    }
    lines
}

fn checked_add(left: usize, right: usize, context: &str) -> Result<usize> {
    left.checked_add(right)
        .ok_or_else(|| BrowserError::Layout(format!("integer overflow while computing {context}")))
}

fn checked_mul(left: usize, right: usize, context: &str) -> Result<usize> {
    left.checked_mul(right)
        .ok_or_else(|| BrowserError::Layout(format!("integer overflow while computing {context}")))
}
