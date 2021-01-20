import json
from itertools import chain
from shapely.geometry import Polygon, MultiPolygon
import pickle

class GeoJsonHandler(object):

    def __init__(self, input_dir):

        self.geojson_dir = input_dir

        with open(self.geojson_dir) as f:

            self.data = json.load(f)

        self.polygon = self.definePolygon()

    def definePolygon(self):

        # Load geojson for all German states and select NRW
        for feature in self.data['features']:

            # Select the state of NRW
            if feature['properties']['NAME_1'] == 'Nordrhein-Westfalen':
                # list containing all NRW coordinates
                nrw_coords = feature['geometry']['coordinates']

        # Unlist nrw_coords
        nrw_coords = list(chain(*nrw_coords))

        nrw_coords_tuples = [tuple(elem) for elem in nrw_coords]

        # It is a closed polygon
        # TODO add assert statement to verify that it is a closed polygon
        polygon = Polygon(nrw_coords_tuples)

        return polygon

    def returnTileCoords(self, path_to_pickle):

        # Tile_coords specifies almost 600,000 tiles.
        with open(path_to_pickle, "rb") as f:

            Tile_coords = pickle.load(f)

        return Tile_coords

