from unittest import TestCase
from unittest.mock import patch

from gameplan.install import check_frappe_version


class TestInstall(TestCase):
	def test_frappe_15_is_rejected(self):
		with patch("frappe.__version__", "15.99.0"):
			with self.assertRaisesRegex(SystemExit, "version 16 or above"):
				check_frappe_version()

	def test_frappe_16_and_newer_are_supported(self):
		for version in ("16.0.0-dev", "16.28.0", "17.0.0-dev"):
			with self.subTest(version=version), patch("frappe.__version__", version):
				check_frappe_version()
