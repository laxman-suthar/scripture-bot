from django.contrib import admin
from django.utils.html import format_html
from .models import BibleVerse


@admin.register(BibleVerse)
class BibleVerseAdmin(admin.ModelAdmin):
    list_display = ('book', 'chapter', 'verse', 'text_preview', 'has_embedding')
    list_filter = ('book',)
    search_fields = ('book', 'text')
    list_per_page = 50
    readonly_fields = ('embedding_preview',)

    def text_preview(self, obj):
        """Show first 80 characters of verse text."""
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Text'

    def has_embedding(self, obj):
        """Show ✅ or ❌ in the list view."""
        if obj.embedding is not None and len(obj.embedding) > 0:
            return format_html('<span style="color: #0f0;">✅</span>')
        return format_html('<span style="color: #f00;">❌</span>')
    has_embedding.short_description = 'Embedding'

    def embedding_preview(self, obj):
        """Show first 10 dimensions of the embedding on the detail page."""
        if obj.embedding is None:
            return "No embedding generated"
        dims = list(obj.embedding)
        total = len(dims)
        preview = ', '.join(f'{v:.6f}' for v in dims[:10])
        return format_html(
            '<code>[{}, ...]</code><br>'
            '<small style="color: #888;">Total dimensions: {}</small>',
            preview, total
        )
    embedding_preview.short_description = 'Embedding Vector (preview)'
