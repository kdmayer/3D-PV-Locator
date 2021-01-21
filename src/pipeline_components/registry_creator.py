import geopandas as gpd
import pandas as pd
from shapely import wkt

# Create Tile_coords_Essen.pickle
# ...
# Load PV polygons from our PV_db database file
# Buffer polygons
# Dissolve geometries
# Explode multipart to singleparts
# Load rooftop polygons

class RegistryCreator():

    def __init__(self, configuration):

        # Load PV database file and convert it to a Geopandas.GeoDataFrame with EPSG:4326 as the coordinate reference system
        PV_db = pd.read_csv(configuration['pv_db_path'], sep=';', header=None, names=['Current_Tile_240', 'UL_Image_16', 'geometry'])

        PV_db['geometry'] = PV_db['geometry'].apply(wkt.loads)

        self.PV_gdf = gpd.GeoDataFrame(PV_db, geometry='geometry')
        self.PV_gdf.crs = {"init": "epsg:4326"}
        self.PV_gdf['class'] = int(1)
        self.PV_gdf = self.PV_gdf[['class', 'geometry']]

    def _merge_splitted_PVs(self):

        # Buffer polygons, i.e. overwrite the original polygons with their buffered versions
        # Based on our experience, the buffer value should be within [1e-6, 1e-8]
        self.PV_gdf['geometry'] = self.PV_gdf['geometry'].buffer(1e-6)

        # Dissolve, i.e. aggregate, all PV polygons into one Multipolygon
        self.PV_gdf = self.PV_gdf.dissolve(by="class")

        # Explode multi-part geometries into multiple single geometries
        self.PV_gdf = self.PV_gdf.explode().reset_index().drop(columns=['level_1'])

        self.PV_gdf['raw_area_sqm'] = self.PV_gdf['geometry'].to_crs(epsg=5243).area





    def run(self):

        self._merge_splitted_PVs()

        print(self.PV_gdf)

