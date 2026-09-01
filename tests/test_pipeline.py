import unittest

import pandas as pd

from src.pipeline import ndcg, pairwise_jaccard


class PipelineTests(unittest.TestCase):
    def test_pairwise_jaccard_is_symmetric_and_bounded(self):
        matrix = pd.DataFrame(
            {"c1": [1.0, 0.5], "c2": [0.5, 1.0]},
            index=["a", "b"],
        )
        similarity, common, coverage = pairwise_jaccard(matrix, 2)
        self.assertTrue((similarity.to_numpy() == similarity.to_numpy().T).all())
        self.assertTrue(((similarity.to_numpy() >= 0) & (similarity.to_numpy() <= 1)).all())
        self.assertEqual(common.loc["a", "b"], 2)
        self.assertEqual(coverage.loc["a", "b"], 1.0)

    def test_ndcg_perfect_ranking(self):
        self.assertEqual(ndcg(["a", "b", "c"], {"a", "b"}), 1.0)


if __name__ == "__main__":
    unittest.main()
