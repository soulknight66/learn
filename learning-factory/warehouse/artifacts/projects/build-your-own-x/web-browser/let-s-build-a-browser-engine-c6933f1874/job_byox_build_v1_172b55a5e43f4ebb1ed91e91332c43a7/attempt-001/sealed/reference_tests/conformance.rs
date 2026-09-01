use std::cell::Cell;

use pocket_browser::css::parse_stylesheet;
use pocket_browser::engine::{BrowserEngine, Transport};
use pocket_browser::html::parse_document;
use pocket_browser::http::parse_response;
use pocket_browser::layout::{layout_document, Layout};
use pocket_browser::paint::{paint, MAX_CANVAS_PIXELS};
use pocket_browser::style::{style_document, Color};
use pocket_browser::url::Url;
use pocket_browser::{BrowserError, EngineLimits, Result};

#[test]
fn url_accepts_default_port_and_query_only_target() {
    let url = Url::parse("HTTP://LOCALHOST?x=1").unwrap();
    assert_eq!(url.scheme, "http");
    assert_eq!(url.host, "localhost");
    assert_eq!(url.port, 80);
    assert_eq!(url.path_and_query, "/?x=1");
    assert_eq!(url.authority(), "localhost");
}

#[test]
fn url_rejects_invalid_authorities_and_fragments() {
    for input in [
        "http://",
        "http://bad..test/",
        "http://-bad.test/",
        "http://bad.test:0/",
        "http://[::1]/",
        "http://good.test/#fragment",
    ] {
        assert!(Url::parse(input).is_err(), "unexpectedly accepted {input}");
    }
}

#[test]
fn response_allows_identical_lengths_but_not_trailing_bytes() {
    let limits = EngineLimits::default();
    let bytes = b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx";
    assert_eq!(parse_response(bytes, &limits).unwrap().body, "x");
    assert!(parse_response(
        b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nxy",
        &limits
    )
    .is_err());
}

#[test]
fn response_checks_header_and_body_limits_at_boundaries() {
    let exact_head = b"HTTP/1.1 200 OK\r\nX: y";
    let mut response = exact_head.to_vec();
    response.extend_from_slice(b"\r\n\r\nok");
    let exact = EngineLimits {
        max_header_bytes: exact_head.len(),
        max_body_bytes: 2,
        ..EngineLimits::default()
    };
    assert_eq!(parse_response(&response, &exact).unwrap().body, "ok");

    let too_small = EngineLimits {
        max_header_bytes: exact_head.len() - 1,
        ..exact
    };
    assert!(parse_response(&response, &too_small).is_err());
    let short_body_budget = EngineLimits {
        max_body_bytes: 1,
        ..exact
    };
    assert!(parse_response(&response, &short_body_budget).is_err());
}

#[test]
fn response_rejects_folding_controls_and_invalid_utf8() {
    let limits = EngineLimits::default();
    for bytes in [
        &b"HTTP/1.1 200 OK\r\nX: first\r\n second\r\n\r\n"[..],
        &b"HTTP/1.1 200 OK\r\nX:\tvalue\r\n\r\n"[..],
        &b"HTTP/2 200 OK\r\n\r\n"[..],
        &b"HTTP/1.1 200 OK\r\n\r\n\xff"[..],
    ] {
        assert!(parse_response(bytes, &limits).is_err());
    }
}

#[test]
fn html_enforces_node_and_depth_budgets() {
    let two_nodes = EngineLimits {
        max_nodes: 2,
        ..EngineLimits::default()
    };
    assert!(parse_document("<p>x</p>", &two_nodes).is_ok());
    assert!(parse_document(
        "<p>x</p>",
        &EngineLimits {
            max_nodes: 1,
            ..two_nodes
        }
    )
    .is_err());

    let one_level = EngineLimits {
        max_dom_depth: 1,
        ..EngineLimits::default()
    };
    assert!(parse_document("<p>x</p>", &one_level).is_ok());
    assert!(parse_document("<p><b>x</b></p>", &one_level).is_err());
}

#[test]
fn html_rejects_ambiguous_or_malformed_markup() {
    let limits = EngineLimits::default();
    for input in [
        "<p id=\"a\" id=\"b\"></p>",
        "<p class=unquoted></p>",
        "<p></div>",
        "<p>&copy;</p>",
        "<!-- never closed",
    ] {
        assert!(parse_document(input, &limits).is_err(), "accepted {input}");
    }
}

#[test]
fn css_rejects_combinators_nesting_and_bad_values() {
    assert!(parse_stylesheet("main p { color: red; }").is_err());
    assert!(parse_stylesheet("p { color: red; nested { width: 1px; } }").is_err());
    assert!(parse_stylesheet("p { color red; }").is_err());
    assert!(parse_stylesheet("/* open").is_err());

    let document = parse_document("<p>x</p>", &EngineLimits::default()).unwrap();
    let invalid = parse_stylesheet("aside { width: -1px; }").unwrap();
    assert!(style_document(&document, &invalid).is_err());
}

#[test]
fn later_equal_specificity_wins() {
    let document = parse_document(
        "<p class=\"notice\">x</p>",
        &EngineLimits::default(),
    )
    .unwrap();
    let sheet = parse_stylesheet(
        ".notice { color: #010203; } .notice { color: #040506; }",
    )
    .unwrap();
    let styled = style_document(&document, &sheet).unwrap();
    assert_eq!(styled[0].color, Color { r: 4, g: 5, b: 6 });
}

#[test]
fn layout_wraps_long_words_and_stacks_margin_boxes() {
    let document = parse_document(
        "<p>abcdef</p><p>z</p>",
        &EngineLimits::default(),
    )
    .unwrap();
    let sheet = parse_stylesheet("p { margin: 1px; }").unwrap();
    let styled = style_document(&document, &sheet).unwrap();
    let layout = layout_document(&styled, 6).unwrap();
    assert_eq!(
        layout.boxes[0].children[0].text_lines,
        vec!["abcd".to_string(), "ef".to_string()]
    );
    assert!(layout.boxes[0].rect.y + layout.boxes[0].rect.height <= layout.boxes[1].rect.y);
}

#[test]
fn child_background_paints_over_parent() {
    let document = parse_document(
        "<main><p>x</p></main>",
        &EngineLimits::default(),
    )
    .unwrap();
    let sheet = parse_stylesheet(
        "main { background: #ff0000; } p { background: #0000ff; }",
    )
    .unwrap();
    let styled = style_document(&document, &sheet).unwrap();
    let layout = layout_document(&styled, 8).unwrap();
    let canvas = paint(&layout).unwrap();
    assert_eq!(canvas.pixel(0, 0), Some(Color { r: 0, g: 0, b: 255 }));
    assert_eq!(canvas.pixel(8, 0), None);
}

#[test]
fn paint_rejects_excessive_canvas_before_allocation() {
    let layout = Layout {
        width: 1,
        height: MAX_CANVAS_PIXELS + 1,
        boxes: Vec::new(),
    };
    assert!(matches!(paint(&layout), Err(BrowserError::Layout(_))));
}

struct CountingTransport {
    calls: Cell<usize>,
    bytes: Vec<u8>,
}

impl Transport for CountingTransport {
    fn exchange(&self, _url: &Url, _request: &[u8], _limit: usize) -> Result<Vec<u8>> {
        self.calls.set(self.calls.get() + 1);
        Ok(self.bytes.clone())
    }
}

#[test]
fn engine_rejects_status_and_media_type_after_one_exchange() {
    for response in [
        b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n".to_vec(),
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}"
            .to_vec(),
    ] {
        let transport = CountingTransport {
            calls: Cell::new(0),
            bytes: response,
        };
        let engine = BrowserEngine::new(EngineLimits::default(), 10);
        assert!(matches!(
            engine.load("http://example.test/", "", &transport),
            Err(BrowserError::Http(_))
        ));
        assert_eq!(transport.calls.get(), 1);
    }
}

#[test]
fn engine_rejects_a_transport_that_ignores_its_budget() {
    let limits = EngineLimits {
        max_header_bytes: 8,
        max_body_bytes: 8,
        ..EngineLimits::default()
    };
    let transport = CountingTransport {
        calls: Cell::new(0),
        bytes: vec![b'x'; 21],
    };
    let engine = BrowserEngine::new(limits, 10);
    assert!(matches!(
        engine.load("http://example.test/", "", &transport),
        Err(BrowserError::Network(_))
    ));
    assert_eq!(transport.calls.get(), 1);
}
