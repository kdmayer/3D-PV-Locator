import pickle
from pathlib import Path
import pandas as pd
import os

class TileCoordsUpdater(object):
    """
    In case the tile processing is halted or aborted, this class can be used to update the list of tiles by removing all the already processed tiles.

    Attributes
    ----------
    old_tile_coords : list
        List of tuples with all the tiles within the selected county.
    county : str
        The name of the county for which you run the analysis.
    tile_coords_path : Path
        Path to the pickle file which stores the list of tuples for all tiles within a given county.
    processed_path : Path
        Path to the .csv file which stores all the already processed tiles within a given county.
    """

    def __init__(self, configuration=None, tile_coords=None):
        """
        Parameters
        ----------
        configuration : dict
            The configuration based on config.yml in dict format.
        tile_coords : list
            List of tuples, where each tuple specifies the to be downloaed tiles by their minx, miny, maxx, maxy coordinates.
        """

        self.old_tile_coords = tile_coords

        self.county = configuration['county4analysis']

        self.tile_coords_path = Path(f"data/coords/{self.county}.pickle")

        self.processed_path = Path(f"logs/processing/{self.county}_processedTiles.csv")

    def update(self):
        """
        Removes all the already processed tiles within a given county from the list of tiles which ought to be processed.
        """

        if os.path.exists(self.processed_path):

            # Load Processed.csv file
            processedTiles_df = pd.read_table(self.processed_path, header=None)

            processedTiles_df = processedTiles_df.drop_duplicates()

            processedTiles_list = []

            for index, tile in processedTiles_df.iterrows():

                minx, miny, maxx, maxy = tile[0].replace(",COMPLETE.png", "").split(',')

                processedTiles_list.append((float(minx), float(miny), float(maxx), float(maxy)))

            new_Tile_coords = [item for item in self.old_tile_coords if item not in processedTiles_list]

            print(
                f"Old list of tiles contained {len(self.old_tile_coords)} elements. New list contains {len(new_Tile_coords)}")

            print(
                f"Successfully updated {self.county}.pickle by removing {len(self.old_tile_coords) - len(new_Tile_coords)} tiles.")

            # Save the new Tile_coords.pickle file
            with open(Path(self.tile_coords_path), 'wb') as f:

                pickle.dump(new_Tile_coords, f)

        else:

            print("ProcessedTiles.csv does not exist. Cannot update TileCoords.pickle by removing already processed tiles ...")





