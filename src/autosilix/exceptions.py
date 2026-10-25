"""AutoSilix Exception Hierarchy."""


class AutoSilixError(Exception):
    """Base exception for all AutoSilix errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


class ConfigurationError(AutoSilixError):
    """Raised when configuration parsing or validation fails."""


class ValidationError(AutoSilixError):
    """Raised when schema validation or input validation fails."""


class ToolNotFoundError(AutoSilixError):
    """Raised when a required EDA tool executable cannot be located."""


class ToolExecutionError(AutoSilixError):
    """Raised when an external EDA tool exits with a non-zero exit code."""

    def __init__(
        self,
        message: str,
        stage: str,
        exit_code: int | None = None,
        log_path: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details)
        self.stage = stage
        self.exit_code = exit_code
        self.log_path = log_path


class StageTimeoutError(AutoSilixError):
    """Raised when a stage exceeds its configured execution timeout."""

    def __init__(self, stage: str, timeout_seconds: float) -> None:
        super().__init__(
            f"Stage '{stage}' timed out after {timeout_seconds:.1f} seconds",
            details=f"Configured timeout: {timeout_seconds}s",
        )
        self.stage = stage
        self.timeout_seconds = timeout_seconds


class DependencyError(AutoSilixError):
    """Raised when stage prerequisites are not satisfied."""


class ArtifactError(AutoSilixError):
    """Raised when artifact management, creation, or verification fails."""


class ManifestError(AutoSilixError):
    """Raised when manifest generation, loading, or validation fails."""


class MetricsExtractionError(AutoSilixError):
    """Raised when metrics cannot be parsed or source reports are missing/malformed."""


class IncompatibleComparisonError(AutoSilixError):
    """Raised when attempting to compare incompatible runs (e.g. mismatched designs/PDKs)."""
