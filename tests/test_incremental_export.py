# coding=utf-8

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from trendradar.exports.incremental import (
    build_incremental_payload,
    write_incremental_package,
)
from trendradar.storage.base import NewsData, NewsItem, RSSData, RSSItem


class IncrementalExportTests(unittest.TestCase):
    def test_build_payload_only_contains_items_added_since_baseline(self):
        before_news = NewsData(
            date="2026-07-18",
            crawl_time="10-00",
            items={
                "gov": [
                    NewsItem(
                        title="Existing policy",
                        source_id="gov",
                        source_name="Government",
                        rank=2,
                        url="https://example.com/existing",
                    )
                ]
            },
        )
        after_news = NewsData(
            date="2026-07-18",
            crawl_time="10-20",
            items={
                "gov": [
                    NewsItem(
                        title="Existing policy (updated title)",
                        source_id="gov",
                        source_name="Government",
                        rank=1,
                        url="https://example.com/existing",
                    ),
                    NewsItem(
                        title="New policy",
                        source_id="gov",
                        source_name="Government",
                        rank=3,
                        url="https://example.com/new",
                        first_time="10-20",
                        last_time="10-20",
                    ),
                ]
            },
        )
        before_rss = RSSData(
            date="2026-07-18",
            crawl_time="10:00",
            items={
                "finance": [
                    RSSItem(
                        title="Existing RSS",
                        feed_id="finance",
                        feed_name="Finance RSS",
                        url="https://example.com/rss/existing",
                    )
                ]
            },
        )
        after_rss = RSSData(
            date="2026-07-18",
            crawl_time="10:20",
            items={
                "finance": [
                    RSSItem(
                        title="Existing RSS",
                        feed_id="finance",
                        feed_name="Finance RSS",
                        url="https://example.com/rss/existing",
                    ),
                    RSSItem(
                        title="New RSS",
                        feed_id="finance",
                        feed_name="Finance RSS",
                        url="https://example.com/rss/new",
                        published_at="2026-07-18T10:18:00+08:00",
                    ),
                ]
            },
        )

        payload = build_incremental_payload(
            before_news=before_news,
            after_news=after_news,
            before_rss=before_rss,
            after_rss=after_rss,
            generated_at="2026-07-18T10:21:00+08:00",
            batch_metadata={"run_id": "123", "run_attempt": "1"},
            failed_news_ids=["failed-news"],
            failed_rss_ids=["failed-rss"],
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["counts"], {"news": 1, "rss": 1, "total": 2})
        self.assertEqual([item["title"] for item in payload["news_items"]], ["New policy"])
        self.assertEqual([item["title"] for item in payload["rss_items"]], ["New RSS"])
        self.assertEqual(payload["failed_sources"]["news"], ["failed-news"])
        self.assertEqual(payload["failed_sources"]["rss"], ["failed-rss"])
        self.assertEqual(payload["batch"]["run_id"], "123")

    def test_write_package_is_valid_gzip_even_when_there_are_no_new_items(self):
        payload = build_incremental_payload(
            before_news=None,
            after_news=None,
            before_rss=None,
            after_rss=None,
            generated_at="2026-07-18T10:21:00+08:00",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / "nested" / "incremental.json.gz"
            result = write_incremental_package(package_path, payload)

            self.assertEqual(result, package_path)
            self.assertFalse(package_path.with_suffix(package_path.suffix + ".tmp").exists())
            with gzip.open(package_path, "rt", encoding="utf-8") as package_file:
                written_payload = json.load(package_file)

        self.assertEqual(written_payload["counts"]["total"], 0)
        self.assertEqual(written_payload["news_items"], [])
        self.assertEqual(written_payload["rss_items"], [])


if __name__ == "__main__":
    unittest.main()
