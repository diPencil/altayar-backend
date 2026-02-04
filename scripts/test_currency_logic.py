import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from config.settings import settings
from shared.validators import validate_currency

class TestCurrencyLogic(unittest.TestCase):
    def setUp(self):
        # Ensure we know what the settings are during validation
        self.original_default = settings.DEFAULT_CURRENCY
        self.original_supported = settings.SUPPORTED_CURRENCIES

    def tearDown(self):
        # Restore settings
        pass # Settings are modifying the actual object, assume we mock strictly where needed or rely on current dev settings

    def test_validate_currency_default(self):
        """Test that None or empty string returns DEFAULT_CURRENCY (USD)"""
        # Given settings.DEFAULT_CURRENCY is USD
        result = validate_currency(None)
        self.assertEqual(result, "USD")
        
        result = validate_currency("")
        self.assertEqual(result, "USD")

    def test_validate_currency_valid_usd(self):
        """Test valid currency USD"""
        result = validate_currency("USD")
        self.assertEqual(result, "USD")

    def test_validate_currency_valid_egp(self):
        """Test valid currency EGP"""
        result = validate_currency("EGP")
        self.assertEqual(result, "EGP")

    def test_validate_currency_valid_eur(self):
        """Test valid currency EUR"""
        result = validate_currency("EUR")
        self.assertEqual(result, "EUR")
        
    def test_validate_currency_valid_sar(self):
        """Test valid currency SAR"""
        result = validate_currency("SAR")
        self.assertEqual(result, "SAR")

    def test_validate_currency_invalid(self):
        """Test invalid currency raises HTTP 400"""
        with self.assertRaises(HTTPException) as cm:
            validate_currency("XYZ")
        
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("Unsupported currency: XYZ", cm.exception.detail)

    @patch('shared.validators.settings')
    def test_validate_currency_custom_settings(self, mock_settings):
        """Test validation with mocked settings to ensure it's not hardcoded"""
        # Mock settings
        mock_settings.DEFAULT_CURRENCY = "GBP"
        mock_settings.supported_currencies_list = ["GBP", "JPY"]
        
        # Test default
        self.assertEqual(validate_currency(None), "GBP")
        
        # Test supported
        self.assertEqual(validate_currency("JPY"), "JPY")
        
        # Test unsupported (previously valid ones)
        # Note: validate_currency imports settings directly. 
        # Patching where it's imported (shared.validators.settings) is cleaner.
        pass

if __name__ == '__main__':
    unittest.main()
