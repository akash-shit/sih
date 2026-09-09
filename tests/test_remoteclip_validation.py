import unittest
from pathlib import Path

import numpy as np

from app.config import EMBEDDING_DIM, REMOTECLIP_CHECKPOINT
from app.embeddings.clip_embedder import embed_image_tile, embed_text
from app.geospatial import catalog_db as db


class RemoteClipRealTileValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REMOTECLIP_CHECKPOINT.is_file():
            raise unittest.SkipTest(
                "CHECKPOINT UNAVAILABLE: stage the official RemoteCLIP-ViT-B-32.pt before running real embedding validation."
            )
        with db.get_conn() as conn:
            rows = conn.execute(
                "SELECT tile_path FROM tiles WHERE tile_path IS NOT NULL ORDER BY vector_id"
            ).fetchall()
        cls.tile_paths = [row["tile_path"] for row in rows if Path(row["tile_path"]).is_file()][:2]
        if len(cls.tile_paths) < 2:
            raise unittest.SkipTest("INSUFFICIENT REAL DATA: two local catalog tile files are required.")

    def test_real_tile_and_text_embeddings_are_compatible(self):
        image_vector = embed_image_tile(self.tile_paths[0])
        repeated_vector = embed_image_tile(self.tile_paths[0])
        different_vector = embed_image_tile(self.tile_paths[1])
        text_vector = embed_text("satellite construction development")

        self.assertEqual(image_vector.shape, (EMBEDDING_DIM,))
        self.assertEqual(text_vector.shape, (EMBEDDING_DIM,))
        self.assertTrue(np.isfinite(image_vector).all())
        self.assertTrue(np.isfinite(text_vector).all())
        self.assertAlmostEqual(float(np.linalg.norm(image_vector)), 1.0, places=4)
        self.assertAlmostEqual(float(np.linalg.norm(text_vector)), 1.0, places=4)
        self.assertGreater(float(np.dot(image_vector, repeated_vector)), 0.9999)
        self.assertTrue(np.isfinite(float(np.dot(image_vector, different_vector))))


if __name__ == "__main__":
    unittest.main()