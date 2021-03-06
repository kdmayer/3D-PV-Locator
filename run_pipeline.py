from __future__ import unicode_literals
import yaml
from pathlib import Path
import os
import pandas as pd

from src.pipeline_components.tile_creator import TileCreator
from src.pipeline_components.tile_downloader import TileDownloader
from src.pipeline_components.tile_processor import TileProcessor
from src.pipeline_components.tile_updater import TileCoordsUpdater
from src.utils.geojson_handler import GeoJsonHandler
from src.pipeline_components.registry_creator import RegistryCreator

def main():

    # ------- Read configuration -------

    config_file = 'config.yml'

    with open(config_file, 'rb') as f:

        conf = yaml.load(f, Loader=yaml.FullLoader)

    run_tile_creator = conf.get('run_tile_creator', 0)
    run_tile_downloader = conf.get('run_tile_downloader', 0)
    run_tile_processor = conf.get('run_tile_processor', 0)
    run_tile_updater = conf.get('run_tile_coords_updater', 0)
    run_registry_creator = conf.get('run_registry_creator', 0)

    # Todo: Do the set up for your repo here
    # 1. Use the county variable to only select tiles which lie within your selected county
    # 2. Use the county variable to download the respective rooftop polygons file from AWS S3

    county4analysis = conf.get('county4analysis', 'Essen')
    nrw_county_data_path = conf.get('nrw_county_data_path', 'data/nrw_county_data/nrw_counties.geojson')
    downloaded_path = Path(f"logs/downloading/{county4analysis}_downloadedTiles.csv")
    processed_path = Path(f"logs/processing/{county4analysis}_processedTiles.csv")

    # ------- GeoJsonHandler provides utility functions -------

    county_handler = GeoJsonHandler(nrw_county_data_path, county4analysis)

    # ------- TileCreator creates pickle file with all tiles in NRW and their respective minx, miny, maxx, maxy coordinates -------

    if run_tile_creator:

        print("Starting to create a pickle file with the bounding box coordinates for all tiles within your selected county ... This will take a while")

        tileCreator = TileCreator(county_handler=county_handler)

        tileCreator.defineTileCoords()

        print('Pickle file has been sucessfully created')

    # Tile_coords is a list of tuples. Each tuple specifies its respective tile by minx, miny, maxx, maxy.
    tile_coords = county_handler.returnTileCoords()

    print(f'{len(tile_coords)} tiles have been identified.')

    # ------- TileDownloader downloads tiles from openNRW in a multi-threaded fashion -------

    if run_tile_downloader:

        print('Starting to download ' + str(len(tile_coords)) + '. This will take a while.')

        downloader = TileDownloader(configuration=conf, polygon=county_handler.polygon, tile_coords=tile_coords)

    if os.path.exists(Path(downloaded_path)):

        # Load DownloadedTiles.csv file
        downloadedTiles_df = pd.read_table(downloaded_path, header=None)

        print(f"{downloadedTiles_df[0].nunique()} unique tiles have been successfully downloaded.")

    if run_tile_processor:

        tileProcessor = TileProcessor(configuration=conf, polygon=county_handler.polygon)

        tileProcessor.run()

    if os.path.exists(processed_path):

        # Load DownloadedTiles.csv file
        processedTiles_df = pd.read_table(processed_path, header=None)

        print(f"{processedTiles_df[0].nunique()} unique tiles have been successfully processed.")

    if run_tile_updater:

        updater = TileCoordsUpdater(configuration=conf, tile_coords=tile_coords)

        updater.update()

    if run_registry_creator:

        registryCreator = RegistryCreator(configuration=conf)

        registryCreator.run()


if __name__ == '__main__':

    main()