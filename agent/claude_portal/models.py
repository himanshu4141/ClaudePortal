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
