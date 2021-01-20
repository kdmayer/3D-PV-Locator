import unittest
import pickle
import os

class TestPickleFile(unittest.TestCase):

    def test_length(self):

        with open("/Users/kevin/PV_Pipeline/data/coords/TileCoords.pickle", "rb") as f:

            Tile_coords = pickle.load(f)

        self.assertTrue(len(Tile_coords) == 596722)

if __name__ == '__main__':
    unittest.main()