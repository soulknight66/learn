# CS144: Computer Network — Kickoff Brief

Artifact status: **prepared kickoff, not yet validated**. Completing this unit can never by itself establish completion of the course.

## What this is

This is a bounded, self-contained first study unit for a learner who is already strong in algorithms and wants more practice turning specifications into reliable software. The catalog identifies CS144 as a Stanford computer-networking course using C++, but it does not provide a textbook or assignment text. Accordingly, this kickoff is manager-authored. It is not presented as an official Stanford unit or assignment.

The unit uses a bounded byte stream: a small systems component whose behavior depends on capacity, lifecycle, accounting, and byte ordering. That narrow surface is deliberate. It makes engineering decisions and test evidence visible without requiring prior networking lectures.

## Unit outcome

By the end of the kickoff, you should be able to:

- translate a stateful API contract into invariants before writing code;
- implement partial acceptance, ordered delivery, closure, and error state safely in C++17;
- connect a data-structure choice to observable complexity;
- design deterministic tests around boundaries and state transitions;
- leave a reproducible build, test, and design record for another engineer.

The expected effort is about six hours. Stop at eight hours, preserve the failing evidence, and document the blocker rather than silently expanding the scope.

## Starting assumptions

You should already be comfortable with asymptotic analysis, basic C++ ownership and value semantics, standard containers, and compiling a small CMake project. No networking protocol knowledge is required for this unit.

Use only the contract in STUDY_TASK.md as the authoritative task specification. The work must build and test without network access or third-party downloads.

## Material boundary

Locally available and required:

- COURSE_BRIEF.md
- STUDY_TASK.md
- COMPREHENSION.md

Catalog metadata also contains a course-website link and a video-playlist link. Their contents were not retrieved or verified and they are not needed here. The catalog explicitly lists no textbook. It mentions assignments only by directing readers to the course website; no official assignment content is present.

Do not treat external notes, solution repositories, or linked pages as authoritative for this manager-authored task. If an ambiguity remains, record the question in DESIGN.md and choose the narrowest behavior consistent with the local contract.

## Course boundary

This kickoff covers one software component, not the complete subject of computer networking. Packet formats, Internet layering, routing, reliable transport, congestion control, network applications, and any official CS144 laboratory sequence remain outside the prepared graph. Later course-management jobs must retrieve and classify lawful materials before adding units.

Provenance: manager-authored from the supplied CSDIY catalog snapshot at source commit adce8e13789dc16aa6d1fbe163e9541736defae4; no external retrieval was performed.

Validation label: LEARNER_MATERIAL_PREPARED_NOT_VALIDATED.
