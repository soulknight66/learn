package exitstatus

// Status converts a wait result to a shell-style process status. Signal is zero for normal exits.
func Status(exitCode, signal int) int {
	if signal != 0 {
		return signal
	}
	return exitCode
}
