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

    def test_release_276_tag_tree_inventory_remains_bounded_and_reproducible(self):
        root = Path(__file__).parents[1]
        review = (
            root / 'docs' / 'research' / 'smoldyn-2.75-license-review.md'
        ).read_text(encoding='utf-8')
        third_party = (root / 'THIRD_PARTY.md').read_text(encoding='utf-8')
        normalized_review = ' '.join(review.split())
        normalized_third_party = ' '.join(third_party.split())

        self.assertIn('complete, non-truncated Git tree', normalized_review)
        self.assertIn(
            'root tree `6c71c605a52972a4296b1c696ba8bb25c2bb6fbe`',
            normalized_review,
        )
        self.assertIn('4,727 blobs totalling 249,277,100 bytes', normalized_review)
        self.assertIn('`source/NextSubVolume` | 1,398 files', normalized_review)
        self.assertIn('`source/BioNetGen` | 79 files', normalized_review)
        self.assertIn('`source/pybind11/LICENSE`', normalized_review)
        self.assertIn('`windows/_freeglut/Copying.txt`', normalized_review)
        self.assertIn(
            'does not substitute for an official 2.76 archive hash',
            normalized_review,
        )
        self.assertIn('complete tag-tree component inventory', normalized_third_party)

    def test_release_276_archive_identity_records_the_non_equivalent_distribution(self):
        root = Path(__file__).parents[1]
        review = (
            root / 'docs' / 'research' / 'smoldyn-2.75-license-review.md'
        ).read_text(encoding='utf-8')
        third_party = (root / 'THIRD_PARTY.md').read_text(encoding='utf-8')
        normalized_review = ' '.join(review.split())
        normalized_third_party = ' '.join(third_party.split())

        self.assertIn('39,339,615 bytes', normalized_review)
        self.assertIn(
            '`10fd440dece77ae7304b019943256e08cc87ccef796db33eaf7461fcfb326fd7`',
            normalized_review,
        )
        self.assertIn(
            '3,965 regular files totalling 74,010,835 bytes', normalized_review
        )
        self.assertIn('2,465 path-and-content matches', normalized_review)
        self.assertIn('1,499 archive-only files', normalized_review)
        self.assertIn('2,261 Git-only files', normalized_review)
        self.assertIn('one differing common file', normalized_review)
        self.assertIn('does not contain the tagged root `LICENSE`', normalized_review)
        self.assertIn(
            'not content-equivalent to the pinned Git tree', normalized_review
        )
        self.assertIn('official 2.76 source archive', normalized_third_party)
        self.assertIn(
            'not content-equivalent to the pinned tag tree', normalized_third_party
        )

    def test_release_276_archive_license_inventory_preserves_component_boundaries(self):
        root = Path(__file__).parents[1]
        review = (
            root / 'docs' / 'research' / 'smoldyn-2.75-license-review.md'
        ).read_text(encoding='utf-8')
        third_party = (root / 'THIRD_PARTY.md').read_text(encoding='utf-8')
        normalized_review = ' '.join(review.split())
        normalized_third_party = ' '.join(third_party.split())

        self.assertIn('four license-like regular files', normalized_review)
        self.assertIn(
            '`source/BioNetGen/LICENSE.txt` | 35,147 | '
            '`8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903`',
            normalized_review,
        )
        self.assertIn(
            '`source/libSteve/SFMT/LICENSE.txt` | 1,583 | '
            '`34a32f97ac258a2d8f9f7c9155504c2e3fb97f1ae4b577e18e08ea07eee1f4ed`',
            normalized_review,
        )
        self.assertIn(
            '`source/pybind11/LICENSE` | 1,684 | '
            '`83965b843b98f670d3a85bd041ed4b372c8ec50d7b4a5995a83ac697ba675dcb`',
            normalized_review,
        )
        self.assertIn(
            'all four files match the pinned tag by path and content',
            normalized_review,
        )
        self.assertIn('`windows/_freeglut/Copying.txt`', normalized_review)
        self.assertIn(
            'no standalone license file for NextSubVolume', normalized_review
        )
        self.assertIn('four matching license-like files', normalized_third_party)


if __name__ == '__main__':
    unittest.main()
