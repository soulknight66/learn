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

        if (request.term() < currentTerm) {
            return new VoteDecision(false, currentTerm, Reason.STALE_TERM);
        }
        if (request.term() > currentTerm) {
            currentTerm = request.term();
            votedFor = null;
        }

        boolean candidateUpToDate = request.candidateLastTerm() > localLastTerm
                || (request.candidateLastTerm() == localLastTerm
                        && request.candidateLastOffset() >= localLastOffset);
        if (!candidateUpToDate) {
            return new VoteDecision(false, currentTerm, Reason.LOG_NOT_UP_TO_DATE);
        }
        if (votedFor != null && !votedFor.equals(request.candidateId())) {
            return new VoteDecision(false, currentTerm, Reason.ALREADY_VOTED);
        }
        votedFor = request.candidateId();
        return new VoteDecision(true, currentTerm, Reason.GRANTED);
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
