import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("submit_indexnow.py")
SPEC = importlib.util.spec_from_file_location("submit_indexnow", MODULE_PATH)
assert SPEC and SPEC.loader
INDEXNOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INDEXNOW)


class IndexNowTests(unittest.TestCase):
    def test_current_sitemap_has_expected_canonical_urls(self):
        urls = INDEXNOW.current_urls()
        self.assertEqual(10, len(urls))
        self.assertIn("https://lse6.org/", urls)
        self.assertIn("https://lse6.org/evidence/lse6-expediente-completo.pdf", urls)

    def test_single_canonical_page_change_is_targeted(self):
        active = INDEXNOW.current_urls()
        selected = INDEXNOW.select_changed_urls(
            {"evidencia/index.html"}, active, set()
        )
        self.assertEqual({"https://lse6.org/evidencia/"}, selected)

    def test_global_crawl_change_submits_all_canonical_urls(self):
        active = INDEXNOW.current_urls()
        selected = INDEXNOW.select_changed_urls({"robots.txt"}, active, set())
        self.assertEqual(active, selected)

    def test_tooling_change_does_not_submit_public_urls(self):
        active = INDEXNOW.current_urls()
        selected = INDEXNOW.select_changed_urls(
            {"tools/validate_release.py"}, active, set()
        )
        self.assertEqual(set(), selected)

    def test_key_file_matches_indexnow_contract(self):
        self.assertEqual("LSE6-3001FEC3240DA9D0-616-666", INDEXNOW.read_key())


if __name__ == "__main__":
    unittest.main()
