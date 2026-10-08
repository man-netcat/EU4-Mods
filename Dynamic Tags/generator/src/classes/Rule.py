from dataclasses import dataclass, field
from typing import List


@dataclass
class Rule:
    id: str
    tags: List[str] = field(default_factory=list)
    conditions: str = None
