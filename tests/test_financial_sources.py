# coding=utf-8

import unittest
from unittest.mock import Mock, patch

from trendradar.crawler.sources.base import SourceCrawlContext
from trendradar.crawler.sources.china_policy import fetch_nfra_jgdt
from trendradar.crawler.sources.industry_associations import fetch_cfa_announcement


class FinancialSourceTests(unittest.TestCase):
    def test_nfra_regulatory_updates_filter_by_crawl_date(self):
        payload = {
            "data": {
                "rows": [
                    {
                        "docId": 101,
                        "docSubtitle": "金融监管总局发布监管动态",
                        "publishDate": "2026-07-18 09:30:00",
                        "isTitleLink": "0",
                        "generaltype": "0",
                    },
                    {
                        "docId": 100,
                        "docTitle": "前一日监管动态",
                        "publishDate": "2026-07-17 18:00:00",
                        "isTitleLink": "0",
                    },
                ]
            }
        }
        context = SourceCrawlContext("nfra-jgdt", "2026-07-18")

        with patch("trendradar.crawler.sources.china_policy.fetch", return_value=payload):
            items = fetch_nfra_jgdt(context)

        self.assertEqual([item["title"] for item in items], ["金融监管总局发布监管动态"])
        self.assertIn("itemId=915", items[0]["url"])

    def test_nfra_regulatory_updates_continue_across_full_pages(self):
        current_rows = [
            {
                "docId": index,
                "docTitle": f"当日监管动态 {index}",
                "publishDate": "2026-07-18 09:30:00",
                "isTitleLink": "0",
            }
            for index in range(1, 21)
        ]
        older_row = {
            "docId": 100,
            "docTitle": "前一日监管动态",
            "publishDate": "2026-07-17 18:00:00",
            "isTitleLink": "0",
        }

        def fake_fetch(*args, **kwargs):
            rows = current_rows if kwargs["params"]["pageIndex"] == 1 else [older_row]
            return {"data": {"rows": rows}}

        context = SourceCrawlContext("nfra-jgdt", "2026-07-18")
        with patch("trendradar.crawler.sources.china_policy.fetch", side_effect=fake_fetch) as mocked_fetch:
            items = fetch_nfra_jgdt(context)

        self.assertEqual(len(items), 20)
        self.assertEqual(mocked_fetch.call_count, 2)

    def test_cfa_announcements_use_official_json_results(self):
        response = Mock()
        response.json.return_value = {
            "data": {
                "dataList": [
                    {
                        "docTitle": "关于发布期货业自律规则的通知",
                        "docPubUrl": "/aboutassociation/associationannouncement/202607/a.html",
                        "docRelTime": "2026-07-18",
                    },
                    {
                        "docTitle": "前一日公告",
                        "docPubUrl": "/aboutassociation/associationannouncement/202607/b.html",
                        "docRelTime": "2026-07-17",
                    },
                ]
            }
        }
        context = SourceCrawlContext("cfa-announcement", "2026-07-18")

        with patch("trendradar.crawler.sources.industry_associations.fetch_raw", return_value=response):
            items = fetch_cfa_announcement(context)

        self.assertEqual([item["title"] for item in items], ["关于发布期货业自律规则的通知"])
        self.assertEqual(
            items[0]["url"],
            "https://www.cfachina.org/aboutassociation/associationannouncement/202607/a.html",
        )


if __name__ == "__main__":
    unittest.main()
