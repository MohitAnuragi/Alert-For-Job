import os
import tempfile
import unittest

from checker import is_relevant_job, load_company_whitelist, normalize_company_name


class RelevanceFilterTests(unittest.TestCase):
    def test_allows_entry_level_android_intern(self):
        self.assertTrue(is_relevant_job("Android Developer Intern", "Internship"))

    def test_allows_backend_with_explicit_level(self):
        self.assertTrue(is_relevant_job("Backend Developer", "0-1 years"))

    def test_rejects_ui_design_role(self):
        self.assertFalse(is_relevant_job("UI Designer", ""))

    def test_rejects_senior_role(self):
        self.assertFalse(is_relevant_job("Senior Android Engineer", ""))

    def test_rejects_devops_role(self):
        self.assertFalse(is_relevant_job("DevOps Engineer", ""))

    def test_rejects_generic_software_engineer_without_level(self):
        self.assertFalse(is_relevant_job("Software Engineer", ""))

    def test_normalizes_company_names(self):
        self.assertEqual(normalize_company_name("Razorpay Pvt Ltd"), "razorpay")
        self.assertEqual(normalize_company_name("BrowserStack Technologies"), "browserstack")
        self.assertEqual(normalize_company_name("  Sprinto AI  "), "sprinto")

    def test_loads_company_whitelist_from_csv(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as handle:
            handle.write("Company\nRazorpay Pvt Ltd\nBrowserStack Technologies\n  Sprinto AI  \n")
            temp_path = handle.name

        try:
            approved = load_company_whitelist(temp_path)
            self.assertEqual(approved, {"razorpay", "browserstack", "sprinto"})
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
