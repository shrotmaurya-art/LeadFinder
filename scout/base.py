import abc

class BusinessDataSource(abc.ABC):
    """Abstract base class for all business data sources."""

    @abc.abstractmethod
    def search(self, city: str, category: str) -> list[dict]:
        """Searches for business leads in a given city and category.

        Args:
            city: The city to search in (e.g. 'Virar').
            category: The category of business to search for (e.g. 'Cafes').

        Returns:
            A list of dictionaries representing partially-filled business records.
        """
        pass
