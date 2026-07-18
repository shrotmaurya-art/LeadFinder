from scout.normalize import normalize_phone, normalize_website, normalize_address


class TestNormalizePhone:
    def test_with_plus_and_spaces(self):
        assert normalize_phone("+91 98765 43210") == "+919876543210"

    def test_10_digits_no_country_code(self):
        assert normalize_phone("9876543210") == "+919876543210"

    def test_with_hyphens(self):
        assert normalize_phone("98765-43210") == "+919876543210"

    def test_all_three_equal(self):
        assert normalize_phone("+91 98765 43210") == normalize_phone("9876543210") == normalize_phone("98765-43210") == "+919876543210"

    def test_none_input(self):
        assert normalize_phone(None) is None

    def test_too_short(self):
        assert normalize_phone("123") is None

    def test_91_prefix_12_digits(self):
        assert normalize_phone("919876543210") == "+919876543210"

    def test_starts_with_zero(self):
        assert normalize_phone("09876543210") == "+919876543210"


class TestNormalizeWebsite:
    def test_full_url(self):
        assert normalize_website("https://www.abccafe.in/") == "abccafe.in"

    def test_bare_domain(self):
        assert normalize_website("abccafe.in") == "abccafe.in"

    def test_mixed_case_with_path(self):
        assert normalize_website("ABCCafe.in/menu") == "abccafe.in"

    def test_all_three_equal(self):
        assert normalize_website("https://www.abccafe.in/") == normalize_website("abccafe.in") == normalize_website("ABCCafe.in/menu") == "abccafe.in"

    def test_none_input(self):
        assert normalize_website(None) is None

    def test_empty_string(self):
        assert normalize_website("") is None


class TestNormalizeAddress:
    def test_collapse_whitespace(self):
        assert normalize_address("  Virar   West  ") == "virar west"

    def test_lowercase(self):
        assert normalize_address("MUMBAI") == "mumbai"

    def test_none_input(self):
        assert normalize_address(None) is None
