use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Document {
    pub children: Vec<Node>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Node {
    pub node_type: NodeType,
    pub children: Vec<Node>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NodeType {
    Element(ElementData),
    Text(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ElementData {
    pub tag_name: String,
    pub attributes: BTreeMap<String, String>,
}

impl Node {
    pub fn element(tag_name: String, attributes: BTreeMap<String, String>, children: Vec<Node>) -> Self {
        Self {
            node_type: NodeType::Element(ElementData {
                tag_name,
                attributes,
            }),
            children,
        }
    }

    pub fn text(value: String) -> Self {
        Self {
            node_type: NodeType::Text(value),
            children: Vec::new(),
        }
    }

    pub fn as_element(&self) -> Option<&ElementData> {
        match &self.node_type {
            NodeType::Element(element) => Some(element),
            NodeType::Text(_) => None,
        }
    }
}
