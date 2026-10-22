"""
test_module.py
~~~~~~~~~~~~~~
Verification test suite for drama_downloader package.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import drama_downloader as dd


class TestDramaDownloader(unittest.TestCase):

    def test_rsa_signing(self):
        sig = dd.sign_dramabox("hello")
        self.assertTrue(len(sig) > 100)
        self.assertTrue(sig.startswith("e1Womj1QYXmFgI1NcC9bUFl5LIQLmUV9hjtFjwct"))
        print("[OK] RSA signing test passed (signature identical to Node.js)")

    def test_platform_detection(self):
        cases = [
            ("https://www.dramaboxdb.com/movie/42000001234/drama", "dramabox"),
            ("https://netshort.com/drama/test12345", "netshort"),
            ("https://kisskh.co/Drama/My-Title?id=1234", "kisskh"),
            ("https://www.shortmax.com/drama/sm12345", "shortmax"),
            ("https://freereels.app/drama/fr123456", "freereels"),
            ("https://hongguoduanju.com/detail?series_id=74123456789", "hongguo"),
            ("https://www.dramawave.com/drama/dw12345", "dramawave"),
            ("https://raptdrama.com/drama/12345", "raptdrama"),
            ("https://flextv.com/drama/fx12345", "flextv"),
            ("https://stardusttv.com/video/12345", "stardusttv"),
        ]
        for url, expected in cases:
            plat = dd.detect_platform(url)
            self.assertIsNotNone(plat, f"Failed to detect platform for {url}")
            self.assertEqual(plat.platform_id, expected)
        print(f"[OK] All {len(cases)} platform detection tests passed")

    def test_platforms_list(self):
        platforms = dd.get_all_platforms()
        self.assertGreaterEqual(len(platforms), 11)
        print(f"[OK] Total active platforms: {len(platforms)}")

    def test_vtt_to_srt(self):
        sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello World!

00:00:04.000 --> 00:00:06.000
<b>Welcome to Drama Downloader</b>
"""
        srt = dd.vtt_to_srt(sample_vtt)
        self.assertIn("00:00:01,000 --> 00:00:03,500", srt)
        self.assertIn("1\n", srt)
        self.assertIn("Hello World!", srt)
        self.assertIn("Welcome to Drama Downloader", srt)
        print("[OK] VTT to SRT subtitle conversion test passed")


if __name__ == "__main__":
    unittest.main()
