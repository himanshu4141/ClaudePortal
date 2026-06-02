from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class UsageEvent:
    timestamp: datetime
    session_id: str
    project_path: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )

    @property
    def usage_tokens(self) -> int:
        """Tokens that contribute to rate-limit usage.

        Excludes cache_read_tokens: reading the KV cache is ~10× cheaper than
        regular input and Anthropic's usage meter does not appear to count it
        the same way toward the 5-hour window.
        """
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens
