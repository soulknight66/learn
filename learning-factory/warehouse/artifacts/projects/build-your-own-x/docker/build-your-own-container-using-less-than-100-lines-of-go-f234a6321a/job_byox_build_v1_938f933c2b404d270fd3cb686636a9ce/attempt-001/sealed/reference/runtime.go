package tinycontainer

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
)

// Run launches the current executable in the namespaces described by cfg.
func Run(ctx context.Context, cfg Config, streams IO) error {
	if ctx == nil {
		return fmt.Errorf("run: nil context")
	}
	selfPath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("run: locate current executable: %w", err)
	}
	hostUID, hostGID := currentHostIDs()
	plan, err := BuildLaunchPlan(cfg, selfPath, hostUID, hostGID)
	if err != nil {
		return fmt.Errorf("run: %w", err)
	}

	errorReader, errorWriter, err := os.Pipe()
	if err != nil {
		return fmt.Errorf("run: create child setup pipe: %w", err)
	}
	defer errorReader.Close()

	cmd := exec.CommandContext(ctx, plan.Executable, plan.Arguments...)
	cmd.Stdin = streams.Stdin
	cmd.Stdout = streams.Stdout
	cmd.Stderr = streams.Stderr
	cmd.Env = []string{"PATH=/usr/sbin:/usr/bin:/sbin:/bin"}
	cmd.ExtraFiles = []*os.File{errorWriter}
	if err := configureCommand(cmd, plan); err != nil {
		errorWriter.Close()
		return fmt.Errorf("run: configure child: %w", err)
	}
	if err := cmd.Start(); err != nil {
		errorWriter.Close()
		return fmt.Errorf("run: start child: %w", err)
	}
	if err := errorWriter.Close(); err != nil {
		_ = cmd.Process.Kill()
		_ = cmd.Wait()
		return fmt.Errorf("run: close parent setup descriptor: %w", err)
	}

	setupMessage, readErr := io.ReadAll(io.LimitReader(errorReader, maxChildSetupMessage+1))
	if len(setupMessage) > maxChildSetupMessage {
		// Do not wait while an invalid child remains blocked writing beyond the protocol limit.
		_ = errorReader.Close()
	}
	waitErr := cmd.Wait()
	if readErr != nil {
		return fmt.Errorf("run: read child setup result: %w", readErr)
	}
	if len(setupMessage) > maxChildSetupMessage {
		return fmt.Errorf("run: child setup error exceeded limit")
	}
	if message := strings.TrimSpace(string(setupMessage)); message != "" {
		return fmt.Errorf("run: child setup: %s", message)
	}
	if ctxErr := ctx.Err(); ctxErr != nil {
		return fmt.Errorf("run: contained process canceled: %w", ctxErr)
	}
	if waitErr == nil {
		return nil
	}
	var processExit *exec.ExitError
	if errors.As(waitErr, &processExit) {
		return &ExitError{Code: platformExitCode(processExit)}
	}
	return fmt.Errorf("run: wait for child: %w", waitErr)
}

// RunChildInvocation validates, configures, and execs an internal child invocation.
func RunChildInvocation(args []string) error {
	errorFD := encodedChildErrorFD(args)
	if errorFD >= 0 {
		closeOnExec(errorFD)
	}
	cfg, parsedErrorFD, err := parseChildConfig(args)
	if err != nil {
		reportChildSetupError(errorFD, err)
		return err
	}
	if parsedErrorFD != errorFD {
		err := fmt.Errorf("internal setup descriptor mismatch")
		reportChildSetupError(errorFD, err)
		return err
	}
	if err := enterAndExec(cfg); err != nil {
		reportChildSetupError(errorFD, err)
		return err
	}
	return nil
}

func reportChildSetupError(fd int, setupErr error) {
	if fd != childErrorFD || setupErr == nil {
		return
	}
	file := os.NewFile(uintptr(fd), "tinycontainer-setup-error")
	if file == nil {
		return
	}
	message := setupErr.Error()
	if len(message) >= maxChildSetupMessage {
		message = message[:maxChildSetupMessage-1]
	}
	_, _ = io.WriteString(file, message+"\n")
	_ = file.Close()
}
