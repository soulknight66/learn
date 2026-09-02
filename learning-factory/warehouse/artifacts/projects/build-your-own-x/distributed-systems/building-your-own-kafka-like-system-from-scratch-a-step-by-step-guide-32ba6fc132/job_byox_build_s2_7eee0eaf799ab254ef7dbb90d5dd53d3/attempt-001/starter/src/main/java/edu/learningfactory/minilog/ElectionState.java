package edu.learningfactory.minilog;

import java.util.Objects;

/** Deterministic one-node voting state for leader-term exercises. */
public final class ElectionState {
    public enum Reason {
        GRANTED,
        STALE_TERM,
        LOG_NOT_UP_TO_DATE,
        ALREADY_VOTED
    }

    public record VoteRequest(
            long term,
            String candidateId,
            long candidateLastOffset,
            long candidateLastTerm) {
        public VoteRequest {
            if (term < 0) {
                throw new IllegalArgumentException("term must be non-negative");
            }
            Objects.requireNonNull(candidateId, "candidateId");
            if (candidateId.isBlank()) {
                throw new IllegalArgumentException("candidateId must not be blank");
            }
            validateLogPosition(candidateLastOffset, candidateLastTerm);
        }
    }

    public record VoteDecision(boolean granted, long currentTerm, Reason reason) {
        public VoteDecision {
            Objects.requireNonNull(reason, "reason");
        }
    }

    private long currentTerm;
    private String votedFor;

    public ElectionState(long initialTerm) {
        if (initialTerm < 0) {
            throw new IllegalArgumentException("initialTerm must be non-negative");
        }
        currentTerm = initialTerm;
    }

    public synchronized VoteDecision requestVote(
            VoteRequest request,
            long localLastOffset,
            long localLastTerm) {
        Objects.requireNonNull(request, "request");
        validateLogPosition(localLastOffset, localLastTerm);
        throw new UnsupportedOperationException("TODO milestone 4: implement voting rules");
    }

    public synchronized long currentTerm() {
        return currentTerm;
    }

    public synchronized String votedFor() {
        return votedFor;
    }

    private static void validateLogPosition(long offset, long term) {
        if (offset < -1 || term < -1 || (offset == -1) != (term == -1)) {
            throw new IllegalArgumentException(
                    "empty logs use offset=-1 and term=-1; non-empty positions are non-negative");
        }
    }
}
