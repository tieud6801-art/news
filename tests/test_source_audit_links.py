# coding=utf-8

import unittest
from pathlib import Path

import yaml

from trendradar.crawler.sources.china_policy import NFRA_ITEM_LIST_URLS
from trendradar.report.html_newsnow import render_newsnow_html_content


class SourceAuditLinkTests(unittest.TestCase):
    def test_all_enabled_platforms_have_auditable_source_url(self):
        config = yaml.safe_load(Path("config/config.yaml").read_text(encoding="utf-8"))

        for source in config["platforms"]["sources"]:
            with self.subTest(source_id=source["id"]):
                self.assertRegex(source.get("source_url", ""), r"^https?://")

    def test_nfra_source_links_include_required_frontend_route(self):
        config = yaml.safe_load(Path("config/config.yaml").read_text(encoding="utf-8"))
        sources = {source["id"]: source for source in config["platforms"]["sources"]}

        for source_id, expected_url in NFRA_ITEM_LIST_URLS.items():
            with self.subTest(source_id=source_id):
                self.assertEqual(sources[source_id]["source_url"], expected_url)
                self.assertNotIn("原银保监会", sources[source_id]["name"])

    def test_zero_item_card_title_links_to_configured_source(self):
        source_url = "https://example.com/original-list"
        html = render_newsnow_html_content(
            report_data={"stats": [], "new_titles": [], "failed_ids": []},
            total_titles=0,
            standalone_data={
                "platforms": [
                    {
                        "id": "example",
                        "name": "示例来源",
                        "source_url": source_url,
                        "total_count": 0,
                        "items": [],
                    }
                ],
                "rss_feeds": [],
            },
        )

        self.assertIn(f'href="{source_url}"', html)
        self.assertIn('class="card-name source-link"', html)

    def test_card_title_falls_back_to_first_news_url(self):
        article_url = "https://example.com/news/1"
        html = render_newsnow_html_content(
            report_data={"stats": [], "new_titles": [], "failed_ids": []},
            total_titles=1,
            standalone_data={
                "platforms": [
                    {
                        "id": "legacy",
                        "name": "旧配置来源",
                        "total_count": 1,
                        "items": [{"title": "测试新闻", "url": article_url}],
                    }
                ],
                "rss_feeds": [],
            },
        )

        self.assertIn(
            f'<a href="{article_url}" target="_blank" rel="noopener noreferrer" '
            'class="card-name source-link"',
            html,
        )


if __name__ == "__main__":
    unittest.main()
