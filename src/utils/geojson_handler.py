import json
from itertools import chain
from shapely.geometry import Polygon, MultiPolygon
import pickle

class GeoJsonHandler(object):

    def __init__(self, input_dir, name="Nordrhein-Westfalen"):

        self.geojson_dir = input_dir

        with open(self.geojson_dir) as f:

            self.data = json.load(f)

        self.polygon = self.definePolygon(name)

    def definePolygon(self, name):

        # name should either be "Nordrhein-Westfalen" which is the overall state we are analyzing OR a single county within that state
        if name == "Nordrhein-Westfalen":

            # Load geojson for all German states and select NRW
            for feature in self.data['features']:

                if name == "Nordrhein-Westfalen":

                    # Select the state of NRW
                    if feature['properties']['NAME_1'] == "Nordrhein-Westfalen":
                        # list containing all NRW coordinates
                        coords = feature['geometry']['coordinates']

        else:

            for feature in self.data['features']:

                if feature["properties"]['NAME_3'] == name:

                    coords = feature['geometry']['coordinates']

        # Unlist coords
        coords = list(chain(*coords))

        coords_tuples = [tuple(elem) for elem in coords]

        # It is a closed polygon
        # TODO add assert statement to verify that it is a closed polygon
        polygon = Polygon(coords_tuples)

        return polygon

    def returnTileCoords(self, path_to_pickle):

        with open(path_to_pickle, "rb") as f:

            Tile_coords = pickle.load(f)

        return Tile_coords

