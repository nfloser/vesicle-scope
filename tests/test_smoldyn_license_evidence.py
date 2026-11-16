import unittest
from pathlib import Path


class SmoldynLicenseEvidenceTests(unittest.TestCase):
    def test_release_276_recheck_preserves_the_integration_blocker(self):
        root = Path(__file__).parents[1]
        review = (
            root / 'docs' / 'research' / 'smoldyn-2.75-license-review.md'
        ).read_text(encoding='utf-8')
        third_party = (root / 'THIRD_PARTY.md').read_text(encoding='utf-8')
        normalized_review = ' '.join(review.split())
        normalized_third_party = ' '.join(third_party.split())

        self.assertIn('2.76, dated 2026-10-21', normalized_review)
        self.assertIn('tag `v2.76`', normalized_review)
        self.assertIn(
            'annotated tag object `97de63bc1a4f0c4e42c672a5139d3414bc3b4a64`',
            normalized_review,
        )
        self.assertIn(
            'peeled commit `20fbcb965869a79a55a2c4844b35a66d9a2372a3`',
            normalized_review,
        )
        self.assertIn(
            'all three reviewed blob identities match that peeled commit',
            normalized_review,
        )
        self.assertIn('root `LICENSE` remains [GPL v3]', normalized_review)
        self.assertIn(
            'does not replace the hash-verified 2.75 candidate', normalized_review
        )
        self.assertIn(
            'rechecked 2026-11-15 against release 2.76', normalized_third_party
        )
        self.assertIn('No Smoldyn dependency or adapter is approved', normalized_third_party)


if __name__ == '__main__':
    unittest.main()
