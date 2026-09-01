use std::cell::Cell;

use pocket_browser::css::parse_stylesheet;
use pocket_browser::engine::{BrowserEngine, Transport};
use pocket_browser::html::parse_document;
use pocket_browser::http::{build_get_request, parse_response};
use pocket_browser::style::{style_document, Color, Display};
use pocket_browser::url::Url;
use pocket_browser::{BrowserError, EngineLimits, Result};

#[test]
fn url_normalizes_and_request_is_fixed() {
    let url = Url::parse("http://Example.COM:8080/search?q=rust").unwrap();
    assert_eq!(url.host, "example.com");
    assert_eq!(url.port, 8080);
    assert_eq!(url.path_and_query, "/search?q=rust");
    assert_eq!(url.authority(), "example.com:8080");

    let request = String::from_utf8(build_get_request(&url)).unwrap();
    assert_eq!(
        request,
        "GET /search?q=rust HTTP/1.1\r\nHost: example.com:8080\r\nConnection: close\r\nUser-Agent: pocket-browser/1\r\nAccept: text/html\r\n\r\n"
    );
}

#[test]
fn url_rejects_header_injection_and_credentials() {
    assert!(matches!(
        Url::parse("http://safe.test/%0d%0aX-Evil:yes\r\nInjected: true"),
        Err(BrowserError::Url(_))
    ));
    assert!(Url::parse("http://person@safe.test/").is_err());
    assert!(Url::parse("https://safe.test/").is_err());
}

#[test]
fn response_parser_enforces_unambiguous_framing() {
    let limits = EngineLimits {
        max_header_bytes: 256,
        max_body_bytes: 16,
        ..EngineLimits::default()
    };
    let response = parse_response(
        b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 5\r\n\r\nhello",
        &limits,
    )
    .unwrap();
    assert_eq!(response.status, 200);
    assert_eq!(response.header("CONTENT-TYPE"), Some("text/html; charset=utf-8"));
    assert_eq!(response.body, "hello");

    assert!(parse_response(
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
        &limits
    )
    .is_err());
    assert!(parse_response(
        b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Length: 3\r\n\r\nabc",
        &limits
    )
    .is_err());
}

#[test]
fn html_parser_builds_a_typed_tree_and_decodes_entities() {
    let document = parse_document(
        "<!doctype html><!-- note --><main id=\"app\"><p>Hello &amp; Rust</p><br></main>",
        &EngineLimits::default(),
    )
    .unwrap();
    assert_eq!(document.children.len(), 1);
    let main = document.children[0].as_element().unwrap();
    assert_eq!(main.tag_name, "main");
    assert_eq!(main.attributes.get("id").map(String::as_str), Some("app"));
    assert_eq!(document.children[0].children.len(), 2);
    assert_eq!(
        document.children[0].children[0].children[0].node_type,
        pocket_browser::dom::NodeType::Text("Hello & Rust".to_string())
    );
}

#[test]
fn cascade_uses_specificity_and_hides_nodes() {
    let document = parse_document(
        "<main><p id=\"lead\" class=\"note\">Visible</p><script>hidden</script></main>",
        &EngineLimits::default(),
    )
    .unwrap();
    let sheet = parse_stylesheet(
        "p { color: #ff0000; } .note { color: #00ff00; } #lead { color: #0000ff; }",
    )
    .unwrap();
    let styled = style_document(&document, &sheet).unwrap();
    let paragraph = &styled[0].children[0];
    assert_eq!(paragraph.color, Color { r: 0, g: 0, b: 255 });
    assert_eq!(paragraph.children[0].color, paragraph.color);
    assert_eq!(styled[0].children[1].display, Display::None);
}

struct FixtureTransport {
    calls: Cell<usize>,
    response: Vec<u8>,
}

impl Transport for FixtureTransport {
    fn exchange(&self, url: &Url, request: &[u8], max_response_bytes: usize) -> Result<Vec<u8>> {
        self.calls.set(self.calls.get() + 1);
        assert_eq!(url.host, "example.test");
        assert!(request.starts_with(b"GET /page HTTP/1.1\r\n"));
        assert!(self.response.len() <= max_response_bytes);
        Ok(self.response.clone())
    }
}

#[test]
fn engine_runs_the_pipeline_once_and_paints() {
    let body = "<main><p>Hello browser</p></main>";
    let response = format!(
        "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\n\r\n{}",
        body.len(),
        body
    )
    .into_bytes();
    let transport = FixtureTransport {
        calls: Cell::new(0),
        response,
    };
    let engine = BrowserEngine::new(EngineLimits::default(), 20);
    let page = engine
        .load(
            "http://example.test/page",
            "main { background: #112233; padding: 1px; }",
            &transport,
        )
        .unwrap();

    assert_eq!(transport.calls.get(), 1);
    assert_eq!(page.status, 200);
    assert!(page.layout.height > 0);
    assert_eq!(page.canvas.width, 20);
    assert_eq!(page.canvas.pixel(0, 0), Some(Color { r: 17, g: 34, b: 51 }));
}
