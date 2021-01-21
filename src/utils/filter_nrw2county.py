from pathlib import Path
from shapely.geometry import Point
from src.utils.geojson_handler import GeoJsonHandler
import pickle

if __name__ == "__main__":

    # Define the county for which you would like to obtain the coordinate list
    county = "Essen Städte"

    # North-Rhine Westphalia is the state our data source provides images for
    state_handler = GeoJsonHandler(Path('/Users/kevin/PV4GER/data/deutschlandGeoJSON/2_bundeslaender/1_sehr_hoch.geojson'))
    nrw_tile_coords = state_handler.returnTileCoords(path_to_pickle=Path("/Users/kevin/PV4GER/data/coords/TileCoords.pickle"))

    # Load polygon object representing a county, here for the city of Essen
    county_handler = GeoJsonHandler(Path('/Users/kevin/PV4GER/data/deutschlandGeoJSON/4_kreise/1_sehr_hoch.geojson'), name=county)

    # Iterate over all tile coords in TileCoords.pickle and save the one's for which at least one corner (lower left, lower right, upper left, upper right)
    # is inside the county polygon, i.e. county_handler.polygon
    county_tile_coords = [(minx, miny, maxx, maxy) for (minx, miny, maxx, maxy) in nrw_tile_coords if county_handler.polygon.intersects(Point(minx, miny)) |
                            county_handler.polygon.intersects(Point(maxx, miny)) | county_handler.polygon.intersects(Point(minx, maxy)) |
                            county_handler.polygon.intersects(Point(maxx, maxy))]

    with open(Path(f"/Users/kevin/PV4GER/data/coords/{county}.pickle"), 'wb') as f:

        pickle.dump(county_tile_coords, f)

