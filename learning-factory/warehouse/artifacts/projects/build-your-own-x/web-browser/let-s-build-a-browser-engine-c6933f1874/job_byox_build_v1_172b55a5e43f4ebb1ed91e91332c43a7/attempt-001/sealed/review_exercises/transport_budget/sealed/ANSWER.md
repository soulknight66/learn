# `transport_budget` review answer

High: unchecked addition can wrap in optimized builds or panic in checked builds, turning a safety budget into nondeterministic behavior. Use chained `checked_add` and return a structured error.

High: the caller assumes the transport honored the limit. Reject a returned vector whose length exceeds the computed maximum before parsing it.

Medium: call the transport exactly once and only after URL validation and request construction. Parse framing before decoding or interpreting document content. Reject non-2xx status and a present non-HTML media type before HTML parsing.

High for any real network adapter: hostname approval alone is insufficient. Resolve once, reject disallowed address ranges, connect to the approved address, bind the intended host identity to TLS, and repeat policy on redirects. Add connect/read deadlines and a streaming byte cap. The educational standard-library core cannot safely implement HTTPS validation.

Low: tests should capture the supplied maximum, simulate one byte over it, and use a counter to cover every early-return branch.
