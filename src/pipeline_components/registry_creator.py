import geopandas as gpd
import pandas as pd
from shapely import wkt


class RegistryCreator():

    def __init__(self, configuration):

        # Load PV database file and convert it to a Geopandas.GeoDataFrame with EPSG:4326 as the coordinate reference system
        PV_db = pd.read_csv(configuration['pv_db_path'], sep=';', header=None, names=['Current_Tile_240', 'UL_Image_16', 'geometry'])

        PV_db['geometry'] = PV_db['geometry'].apply(wkt.loads)

        self.PV_gdf = gpd.GeoDataFrame(PV_db, geometry='geometry')
        self.PV_gdf.crs = {"init": "epsg:4326"}
        self.PV_gdf['class'] = int(1)
        self.PV_gdf = self.PV_gdf[['class', 'geometry']]
        self.rooftop_gdf = gpd.read_file(configuration['rooftop_polygon_path'])
        self.rooftop_gdf.crs = {"init": "epsg:4326"}


    def _merge_splitted_PVs(self):

        # Buffer polygons, i.e. overwrite the original polygons with their buffered versions
        # Based on our experience, the buffer value should be within [1e-6, 1e-8] degrees
        self.PV_gdf['geometry'] = self.PV_gdf['geometry'].buffer(1e-6)

        # Dissolve, i.e. aggregate, all PV polygons into one Multipolygon
        self.PV_gdf = self.PV_gdf.dissolve(by="class")

        # Explode multi-part geometries into multiple single geometries
        self.PV_gdf = self.PV_gdf.explode().reset_index().drop(columns=['level_1'])

        self.PV_gdf['raw_area_sqm'] = self.PV_gdf['geometry'].to_crs(epsg=5243).area

    def _overlay_ops(self):

        # Intersect PV panels and rooftop polygons to enrich all the PV polygons with the attributes of their respective rooftop polygon
        self.PV_intersection_gdf = gpd.overlay(self.PV_gdf, self.rooftop_gdf, how="intersection")

        # Symmetrcial difference between PV panels and rooftop polygons
        # Symmetrical difference is the opposite of "intersection" and returns geometries that are only part
        # of one of the GeoDataFrames but not of both
        # Is this actually what we want?!
        self.PV_sym_diff = gpd.overlay(self.PV_gdf, self.rooftop_gdf, how="symmetric_difference")

    def run(self):

        self._merge_splitted_PVs()

        self._overlay_ops()








        # Create area_intersection and area_diff for respective layer 

        x = 10


