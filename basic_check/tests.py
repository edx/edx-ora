# coding=utf-8
from django.test import TestCase
import basic_check_util


class BasicCheckTest(TestCase):
    """
    While Ease-based Basic Check has been removed, we do want to validate that some simple scenarios
    will be returned back to the user:
    1) If the initial text has not changed
    2) If the response contains nothing but whitespace
    3) Validate that the user is not banned.
    """

    _INITIAL_DISPLAY = "How much wood could a woodchuck chuck if a woodchuck could chuck wood"
    _GOOD_STUDENT_ID = 42
    _SKIP_BASIC_CHECKS = False  # No longer used. Should be removed on master.

    def test_initial_text_has_not_changed(self):
        success, results = basic_check_util.simple_quality_check(
            self._INITIAL_DISPLAY, self._INITIAL_DISPLAY,
            self._GOOD_STUDENT_ID, self._SKIP_BASIC_CHECKS
        )
        self.assertTrue(success)
        self.assertEqual(results['score'], 0, "Score should be zero since response equals initial display.")

    def test_whitespace_response(self):
        success, results = basic_check_util.simple_quality_check(
            "        ", self._INITIAL_DISPLAY, self._GOOD_STUDENT_ID,
            self._SKIP_BASIC_CHECKS
        )
        self.assertTrue(success)
        self.assertEqual(results['score'], 0, "Score should be zero since response is all whitespace.")

    def test_good_essay(self):
        success, results = basic_check_util.simple_quality_check(
            "This is a perfectly acceptable response.", self._INITIAL_DISPLAY,
            self._GOOD_STUDENT_ID, self._SKIP_BASIC_CHECKS
        )
        self.assertTrue(success)
        self.assertEqual(results['score'], 1, "Score should be 1 since response is fine.")

    def test_unicode_essay(self):
        success, results = basic_check_util.simple_quality_check(
            u"\u6709\u65f6\u5019\uff0c\u4f60\u5403\u4e86\u5427\uff0c\u6709\u65f6\u5019\uff0c\u9152\u5427\u5403\u4f60\u3002"
            , self._INITIAL_DISPLAY,
            self._GOOD_STUDENT_ID, self._SKIP_BASIC_CHECKS
        )
        self.assertTrue(success)
        self.assertEqual(results['score'], 1, "Score should be 1 since response is fine.")
