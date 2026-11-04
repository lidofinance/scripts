import unittest

from utils.ci_vote import select_vote_script


class VoteSelectionTests(unittest.TestCase):
    def setUp(self):
        self.lending = "/checkout/scripts/vote_lido_lend_factories.py"
        self.other = "/checkout/scripts/upgrade_csm0x02.py"

    def test_no_scripts_preserves_no_vote_behavior(self):
        self.assertIsNone(select_vote_script([]))

    def test_one_script_preserves_automatic_selection(self):
        self.assertEqual(select_vote_script([self.other]), self.other)

    def test_multiple_scripts_require_explicit_selection(self):
        with self.assertRaisesRegex(RuntimeError, "More than one"):
            select_vote_script([self.lending, self.other])

    def test_explicit_selection_chooses_only_requested_vote(self):
        self.assertEqual(
            select_vote_script([self.other, self.lending], "vote_lido_lend_factories.py"), self.lending
        )

    def test_unknown_script_does_not_fall_back_to_another_vote(self):
        with self.assertRaisesRegex(RuntimeError, "VOTE_SCRIPT"):
            select_vote_script([self.other], "vote_lido_lend_factories.py")

    def test_requested_script_missing_from_empty_checkout_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "VOTE_SCRIPT"):
            select_vote_script([], "vote_lido_lend_factories.py")

    def test_paths_and_duplicate_matches_are_rejected(self):
        for requested in [self.lending, "../vote_lido_lend_factories.py"]:
            with self.subTest(requested=requested), self.assertRaisesRegex(RuntimeError, "VOTE_SCRIPT"):
                select_vote_script([self.lending], requested)
        with self.assertRaisesRegex(RuntimeError, "VOTE_SCRIPT"):
            select_vote_script([self.lending, self.lending], "vote_lido_lend_factories.py")
