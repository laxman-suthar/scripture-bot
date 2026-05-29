from django.db import models
from pgvector.django import VectorField, IvfflatIndex


class BibleVerse(models.Model):
    """Stores a single Bible verse with its vector embedding for RAG retrieval."""

    book = models.CharField(max_length=50, db_index=True)
    chapter = models.IntegerField(db_index=True)
    verse = models.IntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=768, null=True, blank=True)

    class Meta:
        unique_together = ('book', 'chapter', 'verse')
        ordering = ['book', 'chapter', 'verse']
        indexes = [
            IvfflatIndex(
                fields=['embedding'],
                name='bible_embedding_idx',
                lists=100,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return f"{self.book} {self.chapter}:{self.verse}"

    @property
    def reference(self):
        """Return formatted reference string like 'John 3:16'."""
        return f"{self.book} {self.chapter}:{self.verse}"
