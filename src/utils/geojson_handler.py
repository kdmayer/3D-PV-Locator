import json
from itertools import chain
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import pickle

class GeoJsonHandler(object):

    def __init__(self, nrw_county_data_path, selected_county):

        nrw_county_gdf = gpd.read_file(nrw_county_data_path)

        single_county_gdf = nrw_county_gdf[nrw_county_gdf['GN'] == selected_county].reset_index(drop=True)

        self.polygon = single_county_gdf.loc[0, 'geometry']

        self.name = selected_county

    def returnTileCoords(self):

        with open(f"data/coords/{self.name}.pickle", "rb") as f:

            Tile_coords = pickle.load(f)

        return Tile_coords

