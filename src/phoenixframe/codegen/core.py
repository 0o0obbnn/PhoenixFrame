from abc import ABC, abstractmethod

class AssetParser(ABC):
    """Abstract base class for parsing external test assets."""
    @abstractmethod
    def parse(self, source: str):
        """Parses the given source and returns a structured representation."""
        pass

class CodeGenerator(ABC):
    """Abstract base class for generating code from structured data."""
    @abstractmethod
    def generate(self, data: dict) -> str:
        """Generates code from the given structured data."""
        pass
