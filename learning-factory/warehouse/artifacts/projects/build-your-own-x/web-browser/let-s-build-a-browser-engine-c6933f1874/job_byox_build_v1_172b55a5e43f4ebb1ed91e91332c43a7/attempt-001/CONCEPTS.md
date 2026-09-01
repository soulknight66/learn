# Concepts

## A pipeline is a sequence of trust boundaries

Network bytes are not HTML. An HTTP parser first establishes framing: where headers stop, which length is authoritative, and whether the body is complete. Only then may UTF-8 decoding and markup parsing begin. Keeping each representation in a distinct Rust type prevents accidental stage skipping.

## Parsing needs a budget

Small grammars can still consume unbounded memory or stack. Header bytes, body bytes, DOM node count, and tree depth are independent resources. Check each budget at the point where that resource grows; checking only the original input length is insufficient.

## HTTP ambiguity is a security concern

Two components that disagree about message length can interpret different requests or responses. This project deliberately rejects transfer coding, multiple disagreeing lengths, line folding, control bytes, and trailing bytes after an explicit length. A narrow accepted language is easier to reason about than permissive recovery.

## The cascade is an ordering problem

Selector matching answers whether a rule applies. Cascading separately chooses one declaration per property using a lexicographic key: specificity followed by source order. Inheritance is a later tree operation and applies only to selected properties.

## Layout and paint are different

Layout converts styled content into geometry. Paint consumes geometry in a defined order and clips writes to a finite target. This separation makes overlap, clipping, and stacking behavior testable without needing a font library or window system.

## Dependency injection makes networking testable

The engine owns HTTP semantics but accepts a `Transport`. A memory transport can prove the exact request and return hostile byte fixtures deterministically. A real connector, if added later, needs DNS, address-range, timeout, redirect, and response-size policy that are outside this core.
