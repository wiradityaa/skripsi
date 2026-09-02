import unittest

import numpy as np
import pandas as pd

from src.pipeline_v2 import similarity, validate


class PipelineV2Tests(unittest.TestCase):
    def test_similarity_validation_contract(self):
        matrix = pd.DataFrame(
            {"c1": [1.0, 0.5], "c2": [0.5, 1.0]},
            index=["a", "b"],
        )
        result, _, _ = similarity(matrix, "graph")
        report = validate("graph_test", result)
        self.assertTrue(report["passed"])
        self.assertTrue(np.isfinite(result.to_numpy()).all())


if __name__ == "__main__":
    unittest.main()
