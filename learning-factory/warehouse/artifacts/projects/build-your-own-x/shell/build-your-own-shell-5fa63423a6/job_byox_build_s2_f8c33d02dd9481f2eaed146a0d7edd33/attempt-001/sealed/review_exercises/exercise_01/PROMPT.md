# Review exercise: superficially working job launch

Review `candidate_launch.c`. It often runs a two-stage foreground pipeline successfully during light testing.

List correctness problems involving process groups, inherited signal dispositions, status selection, child cleanup, and terminal ownership. Rank them by user-visible impact, then outline a launch protocol that remains correct when the first child exits before the second fork completes.
