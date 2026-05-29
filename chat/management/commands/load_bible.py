"""
Management command to download KJV Bible data and load it into PostgreSQL with embeddings.

Usage:
    python manage.py load_bible                  # Load all verses
    python manage.py load_bible --limit 100      # Load first 100 verses (for testing)
    python manage.py load_bible --batch-size 20  # Custom batch size
"""
import json
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from chat.models import BibleVerse
from rag.embedder import get_embeddings
from tqdm import tqdm


# KJV Bible JSON source — clean single-file format
BIBLE_JSON_URL = (
    "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
)

# Book name mapping (the JSON uses index-based books)
BOOK_NAMES = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
]


class Command(BaseCommand):
    help = 'Download KJV Bible and load verses into PostgreSQL with Gemini embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of verses to load (0 = all). Useful for testing.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of verses to embed per API call batch.',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Skip verses that already exist in the database.',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        batch_size = options['batch_size']
        skip_existing = options['skip_existing']

        self.stdout.write(self.style.NOTICE('Downloading KJV Bible data...'))
        bible_data = self._download_bible()

        if bible_data is None:
            self.stdout.write(self.style.ERROR('Failed to download Bible data.'))
            return

        # Parse all verses into flat list
        verses = self._parse_verses(bible_data)
        self.stdout.write(self.style.SUCCESS(f'Parsed {len(verses)} total verses.'))

        if limit > 0:
            verses = verses[:limit]
            self.stdout.write(self.style.WARNING(f'Limited to {limit} verses.'))

        # Filter out existing verses if requested
        if skip_existing:
            existing_count = BibleVerse.objects.count()
            if existing_count > 0:
                existing_refs = set(
                    BibleVerse.objects.values_list('book', 'chapter', 'verse')
                )
                verses = [
                    v for v in verses
                    if (v['book'], v['chapter'], v['verse']) not in existing_refs
                ]
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping {existing_count} existing verses. '
                        f'{len(verses)} new verses to load.'
                    )
                )

        if not verses:
            self.stdout.write(self.style.SUCCESS('No new verses to load. Done!'))
            return

        # Process in batches
        total_loaded = 0
        total_batches = (len(verses) + batch_size - 1) // batch_size

        self.stdout.write(
            self.style.NOTICE(
                f'Loading {len(verses)} verses in {total_batches} batches '
                f'(batch size: {batch_size})...'
            )
        )

        for i in tqdm(range(0, len(verses), batch_size), desc="Embedding batches"):
            batch = verses[i:i + batch_size]
            texts = [v['text'] for v in batch]

            embeddings = None
            retry_delay = 0  # Start with 5 seconds delay
            max_delay = 0
            attempt = 1

            while embeddings is None:
                try:
                    embeddings = get_embeddings(texts)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'\n[Attempt {attempt}] Embedding error at batch {i // batch_size + 1}: {e}'
                        )
                    )
                    self.stdout.write(
                        self.style.WARNING(f'Waiting {retry_delay}s before retrying...')
                    )
                    time.sleep(retry_delay)
                    # Exponential backoff
                    retry_delay = min(retry_delay * 2, max_delay)
                    attempt += 1

            # Save to database
            verse_objects = []
            for verse_data, embedding in zip(batch, embeddings):
                verse_objects.append(
                    BibleVerse(
                        book=verse_data['book'],
                        chapter=verse_data['chapter'],
                        verse=verse_data['verse'],
                        text=verse_data['text'],
                        embedding=embedding,
                    )
                )

            BibleVerse.objects.bulk_create(verse_objects, ignore_conflicts=True)
            total_loaded += len(verse_objects)

            # Rate limit: pause briefly between batches
            time.sleep(0.2)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {total_loaded} verses!')
        )

    def _download_bible(self):
        """Download KJV Bible JSON from GitHub."""
        try:
            response = requests.get(BIBLE_JSON_URL, timeout=60)
            response.raise_for_status()
            # Decode using utf-8-sig to automatically handle and strip UTF-8 BOM
            content = response.content.decode('utf-8-sig')
            return json.loads(content)
        except (requests.RequestException, json.JSONDecodeError) as e:
            self.stdout.write(self.style.ERROR(f'Download error: {e}'))
            return None

    def _parse_verses(self, bible_data):
        """Parse the Bible JSON into a flat list of verse dictionaries."""
        verses = []

        for book_idx, book in enumerate(bible_data):
            book_name = BOOK_NAMES[book_idx] if book_idx < len(BOOK_NAMES) else f"Book {book_idx + 1}"
            chapters = book.get('chapters', [])

            for chapter_idx, chapter_verses in enumerate(chapters):
                chapter_num = chapter_idx + 1

                for verse_idx, verse_text in enumerate(chapter_verses):
                    verse_num = verse_idx + 1
                    clean_text = verse_text.strip()

                    if clean_text:
                        verses.append({
                            'book': book_name,
                            'chapter': chapter_num,
                            'verse': verse_num,
                            'text': clean_text,
                        })

        return verses
