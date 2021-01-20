import pickle
from pathlib import Path
import pandas as pd
import os

class TileCoordsUpdater(object):

    def __init__(self, configuration=None, tile_coords=None):

        self.old_tile_coords = tile_coords

        self.tile_coords_path = configuration['tile_coords_path']

        self.processed_path = configuration['processed_path']

    def update(self):

        '''

        input:

        None

        :return:

        pickle file, which contains all tiles that have not yet been processed.

        '''

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
                f"Successfully updated TileCoords.pickle by removing {len(self.old_tile_coords) - len(new_Tile_coords)} tiles.")

            # Save the new Tile_coords.pickle file
            with open(Path(self.tile_coords_path), 'wb') as f:

                pickle.dump(new_Tile_coords, f)

        else:

            print("ProcessedTiles.csv does not exist. Cannot update TileCoords.pickle by removing already processed tiles ...")





