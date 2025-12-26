"""
Unit tests for utils.py - Korean text alignment utilities
"""
import sys
import pytest
from coupang_coupon_issuer.utils import get_visual_width, kor_align, is_pyinstaller


@pytest.mark.unit
class TestGetVisualWidth:
    """Test get_visual_width() function"""

    def test_ascii_characters(self):
        """ASCII characters should have width of 1 each"""
        assert get_visual_width("hello") == 5
        assert get_visual_width("test123") == 7
        assert get_visual_width("ABC") == 3

    def test_korean_characters(self):
        """Korean characters should have width of 2 each"""
        assert get_visual_width("안녕") == 4
        assert get_visual_width("쿠폰") == 4
        assert get_visual_width("할인방식") == 8

    def test_mixed_content(self):
        """Mixed ASCII and Korean should calculate correctly"""
        # 즉시할인쿠폰 = 6 Korean chars = 12 width
        # _ = 1 ASCII = 1 width  
        # 정률할인 = 4 Korean chars = 8 width
        # Total = 21
        assert get_visual_width("즉시할인쿠폰_정률할인") == 21
        assert get_visual_width("쿠폰1") == 5  # 쿠폰 (4) + 1 (1)
        assert get_visual_width("No") == 2

    def test_empty_string(self):
        """Empty string should have width of 0"""
        assert get_visual_width("") == 0

    def test_numbers_and_symbols(self):
        """Numbers and symbols should have width of 1"""
        assert get_visual_width("12345") == 5
        assert get_visual_width("!@#$%") == 5
        assert get_visual_width("1,000원") == 7  # 1,000 (5) + 원 (2)


@pytest.mark.unit
class TestKorAlign:
    """Test kor_align() function"""

    def test_right_align_ascii(self):
        """Right alignment with ASCII text"""
        result = kor_align("test", 10, '>')
        assert result == "      test"
        assert len(result) == 10

    def test_right_align_korean(self):
        """Right alignment with Korean text"""
        result = kor_align("쿠폰", 10, '>')
        # 쿠폰 has visual width of 4, so padding should be 6 spaces
        assert result == "      쿠폰"
        assert get_visual_width(result) == 10

    def test_right_align_mixed(self):
        """Right alignment with mixed content"""
        result = kor_align("쿠폰1", 10, '>')
        # 쿠폰1 has visual width of 5 (4 + 1), so padding should be 5 spaces
        assert result == "     쿠폰1"
        assert get_visual_width(result) == 10

    def test_left_align_ascii(self):
        """Left alignment with ASCII text"""
        result = kor_align("test", 10, '<')
        assert result == "test      "
        assert len(result) == 10

    def test_left_align_korean(self):
        """Left alignment with Korean text"""
        result = kor_align("쿠폰", 10, '<')
        assert result == "쿠폰      "
        assert get_visual_width(result) == 10

    def test_center_align_ascii(self):
        """Center alignment with ASCII text"""
        result = kor_align("test", 10, '^')
        # 4 chars, 6 padding, left=3, right=3
        assert result == "   test   "
        assert len(result) == 10

    def test_center_align_korean(self):
        """Center alignment with Korean text"""
        result = kor_align("쿠폰", 10, '^')
        # visual width 4, padding 6, left=3, right=3
        assert result == "   쿠폰   "
        assert get_visual_width(result) == 10

    def test_exact_width_match(self):
        """Text exactly matching width should have no padding"""
        result = kor_align("test", 4, '>')
        assert result == "test"
        
        result = kor_align("쿠폰", 4, '>')
        assert result == "쿠폰"

    def test_text_wider_than_width(self):
        """Text wider than specified width should not be truncated"""
        result = kor_align("verylongtext", 5, '>')
        assert result == "verylongtext"  # No truncation, just no padding

    def test_empty_string_alignment(self):
        """Empty string should be padded to full width"""
        result = kor_align("", 10, '>')
        assert result == "          "
        assert len(result) == 10

    def test_non_string_input(self):
        """Non-string inputs should be converted to string"""
        result = kor_align(123, 10, '>')
        assert result == "       123"
        assert len(result) == 10


@pytest.mark.unit
class TestIsPyinstaller:
    """Test is_pyinstaller() function"""

    def test_normal_execution(self):
        """Normal Python execution should return False"""
        # In normal execution, sys.frozen should not exist or be False
        assert is_pyinstaller() == False

    def test_pyinstaller_frozen_only(self, monkeypatch):
        """sys.frozen=True but no _MEIPASS should return False"""
        monkeypatch.setattr(sys, 'frozen', True, raising=False)
        # Remove _MEIPASS if it exists
        if hasattr(sys, '_MEIPASS'):
            monkeypatch.delattr(sys, '_MEIPASS')
        
        assert is_pyinstaller() == False

    def test_pyinstaller_full_bundle(self, monkeypatch):
        """Both sys.frozen=True and _MEIPASS should return True"""
        monkeypatch.setattr(sys, 'frozen', True, raising=False)
        monkeypatch.setattr(sys, '_MEIPASS', '/tmp/_MEI123456', raising=False)
        
        assert is_pyinstaller() == True

    def test_meipass_only(self, monkeypatch):
        """_MEIPASS without frozen should return False"""
        monkeypatch.setattr(sys, 'frozen', False, raising=False)
        monkeypatch.setattr(sys, '_MEIPASS', '/tmp/_MEI123456', raising=False)
        
        assert is_pyinstaller() == False
