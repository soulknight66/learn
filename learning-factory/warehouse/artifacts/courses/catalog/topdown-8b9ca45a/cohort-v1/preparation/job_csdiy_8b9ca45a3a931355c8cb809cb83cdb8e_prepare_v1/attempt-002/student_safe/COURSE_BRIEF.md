# Computer Networking: A Top-Down Approach — kickoff brief

This package starts one bounded study unit; it is not a claim that you have begun, covered, or completed the whole course. The source catalog describes a roughly 40-hour UMass course supported by a textbook, a course website, recordings, interactive material, and Wireshark labs. In this workspace those external resources are references only: their contents were not downloaded or verified, and the textbook itself was not supplied.

## Why this unit

You will begin at the application edge and follow one HTTP exchange down to a TCP byte stream. The engineering challenge is deliberately small. The value comes from making boundary assumptions explicit, separating I/O from parsing, testing inconvenient stream fragmentations, bounding resource use, and leaving reproducible evidence.

This is a manager-authored bridge for a learner who is already comfortable with algorithms but wants stronger software-engineering habits. It is not represented as a UMass lecture, textbook chapter, or reproduction of the linked Wireshark assignment.

## Outcomes

By the end of the unit, you should be able to:

- explain why one socket read is not one protocol message;
- express a protocol parser as states and invariants rather than convenient input assumptions;
- test behavior across fragmentation, malformed data, EOF, timeout, and size limits;
- distinguish application-byte evidence from packet-capture evidence; and
- make a small system reproducible for another engineer.

## Working boundary

Plan for about five focused hours. Work against a server fixture on the loopback interface only, so the task does not depend on internet access or modify an external system. Implement one HTTP/1.1 `GET` exchange over plain TCP. TLS, HTTP/2 and HTTP/3, redirects, proxies, authentication, compression, chunked-body decoding, and production-client completeness are outside this unit.

Use a programming language and ordinary test framework you can run locally. Packet-capture software is optional; the required observations can be made at the socket boundary. Do not record credentials, cookies, tokens, or unrelated traffic in evidence.

## Materials you actually have

The local study task and comprehension prompts are sufficient for this kickoff. The catalog also names or links the following optional resources, none of which is required here:

- the UMass course website — linked, not retrieved or access-verified;
- lecture recordings — linked, not retrieved or access-verified;
- *Computer Networking: A Top-Down Approach* — named, but no copy was provided;
- UMass Wireshark assignments — linked as official assignment material, but their content was not retrieved or reproduced; and
- a supplemental GitHub repository — linked in the catalog, not retrieved or classified.

Later course-management jobs may expand the course only after classifying and validating those materials. Completing this kickoff cannot establish completion of the larger course.
