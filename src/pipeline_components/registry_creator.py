import geopandas as gpd
from pathlib import Path
import numpy as np
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from scipy.spatial import cKDTree
import geopy.distance
import geocoder
import time
import math

class RegistryCreator():
    """
    Creates an address-level PV registry for the specified county by bringing together the information obtained from the tile processing step with the county's 3D rooftop data.

    county : str
        Name of the county for which the enrichted automated PV registry is created.
    PV_gdf : GeoDataFrame
        Contains all the identified and segmented PV panels within a given county based on the results from the previous tile processing step.
    rooftop_gdf : GeoDataFrame
        Contains all the rooftop information such as a rooftop's tilt, its azimuth, and its geo-referenced polygon derived from openNRW's 3D building data.
    bing_key : str
        Your Bing API key which is needed to reverse geocode lat, lon values into actual street addresses.
    """

    def __init__(self, configuration):
        """ 
        Parameters
        ----------
        configuration : dict
            The configuration based on config.yml in dict format.
        """

        self.county = configuration.get('county4analysis')

        # Load PV database file and convert it to a Geopandas.GeoDataFrame with EPSG:4326 as the coordinate reference system
        PV_db = pd.read_csv(Path(f"data/pv_database/{self.county}_PV_db.csv"), sep=';', header=None, names=['Current_Tile_240', 'UL_Image_16', 'geometry'])

        PV_db['geometry'] = PV_db['geometry'].apply(wkt.loads)

        self.PV_gdf = gpd.GeoDataFrame(PV_db, geometry='geometry')
        self.PV_gdf.crs = {"init": "epsg:4326"}
        self.PV_gdf['class'] = int(1)
        self.PV_gdf = self.PV_gdf[['class', 'geometry']]

        self.rooftop_gdf = gpd.read_file(Path(f"{configuration['rooftop_data_dir']}/{self.county}.geojson"))
        self.rooftop_gdf.crs = {"init": "epsg:4326"}

        self.bing_key = configuration['bing_key']

    def _dissolve_raw_PVs(self):

        # Buffer polygons, i.e. overwrite the original polygons with their buffered versions
        # Based on our experience, the buffer value should be within [1e-6, 1e-8] degrees
        self.PV_gdf['geometry'] = self.PV_gdf['geometry'].buffer(1e-6)

        # Dissolve, i.e. aggregate, all PV polygons into one Multipolygon
        self.PV_gdf = self.PV_gdf.dissolve(by="class")

        # Explode multi-part geometries into multiple single geometries
        self.PV_gdf = self.PV_gdf.explode().reset_index().drop(columns=['level_1'])

        self.PV_gdf['raw_area'] = self.PV_gdf['geometry'].to_crs(epsg=5243).area

        self.PV_gdf['identifier'] = self.PV_gdf.index.map(lambda id: "polygon_" + str(id))

    def _overlay_ops(self):

        # Intersect PV panels and rooftop polygons to enrich all the PV polygons with the attributes of their respective rooftop polygon
        self.PV_intersection_gdf = gpd.overlay(self.PV_gdf, self.rooftop_gdf, how="intersection")

        # PV polygons which are not on rooftops. This includes free-standing PV units and geometries overhanging from rooftops
        self.PV_diff_gdf = gpd.overlay(self.PV_gdf, self.rooftop_gdf, how="difference")

    def _ckdnearest(self, gdA, gdB):
        """
        Identifies the nearest points of GeoPandas.DataFrame gdB in GeoPandas.DataFrame gdA. Indices need to be resorted before using this function. 
        
        Parameters
        ----------
        gdA : GeoPandas.GeoDataFrame 
            GeoDataFrame which contains a column specifying shapely.geometry.Point objects 
        gdB : GeoPandas.GeoDataFrame
            GeoDataFrame which contains a column specifying shapely.geometry.Point objects 
        Returns
        -------
        GeoPandas.GeoDataFrame 
            Concatenated GeoPandas.GeoDataFrame containing all columns of both GeoDataFrames excluding gdA's geometry plus distance in degrees.
        """

        nA = np.array(list(zip(gdA.geometry.x, gdA.geometry.y)))
        nB = np.array(list(zip(gdB.geometry.x, gdB.geometry.y)))

        btree = cKDTree(nB)

        dist, idx = btree.query(nA, k=1)

        gdf = pd.concat(
            [gdA.reset_index(drop=True), gdB.loc[idx, gdB.columns != 'geometry'].reset_index(drop=True),
             pd.Series(dist, name='dist')], axis=1)

        return gpd.GeoDataFrame(gdf)

    def _calc_distance(self, nearest_address_gdf):

        # Calculate distance between the centroid of the overhanging PV polygon, here points_no_data,
        # and the PV polygon centroid which is intersected with a rooftop polygon, here address_points
        points_no_data = list(zip(nearest_address_gdf['helper_x'], nearest_address_gdf['helper_y']))
        address_points = list(zip(nearest_address_gdf['geometry'].x, nearest_address_gdf['geometry'].y))

        dist = [geopy.distance.geodesic(address, no_data).m for address, no_data in zip(address_points, points_no_data)]

        nearest_address_gdf['calc_dist'] = pd.Series(dist)

        return nearest_address_gdf

    def _append_diff2intersect(self):

        # Remove PV systems from PV_diff_gdf which are free-standing, i.e. only use the ones belonging to a rooftop
        # Free-standing units can be identified by the fact that their raw_area == area_diff
        self.PV_diff_gdf['area_diff'] = self.PV_diff_gdf['geometry'].to_crs(epsg=5243).area
        self.PV_intersection_gdf['area_inter'] = self.PV_intersection_gdf['geometry'].to_crs(epsg=5243).area

        self.PV_diff_gdf['checker'] = self.PV_diff_gdf.raw_area - self.PV_diff_gdf.area_diff

        self.PV_diff_gdf = self.PV_diff_gdf[self.PV_diff_gdf['checker'] > 0]

        self.PV_diff_gdf = self.PV_diff_gdf[['area_diff', 'identifier', 'geometry']]

        # Remove nan values which arise from corrupted rooftop geometries (rare)
        self.PV_diff_gdf = self.PV_diff_gdf[~self.PV_diff_gdf.identifier.isnull()]

        # Compute centroid of overhanging PV system polygons
        self.PV_diff_gdf['geometry'] = self.PV_diff_gdf['geometry'].centroid

        # Select all the PV polygon IDs which have been successfully intersected with a rooftop
        rooftop_pv_ids = self.PV_intersection_gdf.identifier.unique().tolist()

        # Select all the overhanging PV polygons belong to an intersected PV polygon
        self.PV_diff_gdf = self.PV_diff_gdf[self.PV_diff_gdf.identifier.isin(rooftop_pv_ids)]

        # Only consider cut-off geometries larger than 1 sqm
        self.PV_diff_gdf = self.PV_diff_gdf[self.PV_diff_gdf['area_diff'] > 1.0]

        # IMPORTANT: if ckdnearest is used always reset_index before
        self.PV_diff_gdf = self.PV_diff_gdf.reset_index(drop=True)

        # Extract centroid from intersected PV polygons while preserving their polygon geometry
        self.PV_intersection_gdf['geometry_polygon'] = self.PV_intersection_gdf['geometry']
        self.PV_intersection_gdf['geometry'] = self.PV_intersection_gdf['geometry'].centroid
        self.PV_intersection_gdf['centroid_intersect'] = self.PV_intersection_gdf['geometry']

        self.PV_diff_gdf.rename(columns={'identifier':'identifier_diff'}, inplace=True)

        nearest_address_gdf = self._ckdnearest(self.PV_diff_gdf, self.PV_intersection_gdf)

        nearest_address_gdf['helper_x'] = gpd.GeoSeries(nearest_address_gdf['centroid_intersect']).x
        nearest_address_gdf['helper_y'] = gpd.GeoSeries(nearest_address_gdf['centroid_intersect']).y

        # Check if the identifier of the intersected polygon is the same as the identifier of the overhanging polygon
        nearest_address_gdf['checker'] = nearest_address_gdf['identifier_diff'] == nearest_address_gdf['identifier']

        nearest_address_gdf = self._calc_distance(nearest_address_gdf)

        nearest_address_gdf['area_inter'] = nearest_address_gdf['area_diff']

        nearest_address_gdf = nearest_address_gdf[['raw_area', 'identifier', 'Area',
                                         'Azimuth', 'Building_I', 'City', 'PostalCode', 'RoofTopID',
                                         'RooftopTyp', 'Street', 'StreetNumb', 'Tilt', 'area_inter',
                                         'geometry_polygon']]

        nearest_address_gdf.rename(columns={'geometry_polygon': 'geometry'}, inplace=True)

        self.PV_intersection_gdf.geometry = self.PV_intersection_gdf.geometry_polygon

        self.PV_intersection_gdf = self.PV_intersection_gdf[['raw_area', 'identifier', 'Area', 'Azimuth', 'Building_I',
                                                            'City', 'PostalCode', 'RoofTopID', 'RooftopTyp', 'Street', 'StreetNumb',
                                                            'Tilt', 'area_inter', 'geometry']]

        self.PV_intersection_gdf = gpd.GeoDataFrame(self.PV_intersection_gdf.append(nearest_address_gdf)).reset_index(drop=True)

    def _geocode_addresses(self, addresses):

        coordinates = []
        counter = 0

        for i in range(len(addresses)):

            counter += 1
            print(f"Geocode address {addresses[i]} at {counter}/{len(addresses)}")

            # Apply some sleep to ensure to be below 50 requests per second
            time.sleep(0.1)
            address = addresses[i]
            g = geocoder.bing(address, key=self.bing_key)

            if g.status == 'OK':

                coords = g.latlng
                coordinates.append(coords)

            else:

                print('status: {}'.format(g.status))
                coordinates.append(',')

        return coordinates

    def _create_registry(self):

        # Compute share of raw area that the intersected polygon area covers
        self.PV_intersection_gdf['percentage_intersect'] = self.PV_intersection_gdf['area_inter'] / self.PV_intersection_gdf['raw_area']

        self.PV_intersection_gdf['Street_Address'] = self.PV_intersection_gdf['Street'] + ' ' + self.PV_intersection_gdf['StreetNumb']

        # Identify best possible groupby by performing a groupby and deleting all erroneous entries before conducting a second groupby

        # Group intersection by polygon identifier and sum percentage
        self.group_intersection_id = self.PV_intersection_gdf.groupby("identifier").agg({'area_inter':'sum', 'Street':'first', 'Street_Address':'first',
                                                            'raw_area':'first', 'City':'first', 'PostalCode':'first',
                                                            'percentage_intersect':'sum'})

        # Find erroneous polygons whose area after intersection is larger than their original (raw) area
        polygone = self.group_intersection_id[self.group_intersection_id['percentage_intersect'] > 1.1].index.tolist()

        # Filter out erroneous polygons identified above and all their respective sub-parts
        self.PV_intersection_gdf = self.PV_intersection_gdf.drop(self.PV_intersection_gdf.index[(self.PV_intersection_gdf['identifier'].isin(polygone))
                                                                & (self.PV_intersection_gdf['percentage_intersect'] < 1)])

        # Drop duplicate identifiers for erroneous polygons
        self.PV_intersection_gdf = self.PV_intersection_gdf.drop(
            self.PV_intersection_gdf.index[(self.PV_intersection_gdf['identifier'].isin(polygone))
                                           & (self.PV_intersection_gdf['identifier'].duplicated())])

        # Group by polygon identifier
        self.group_intersection_id = self.PV_intersection_gdf.groupby("identifier").agg({'area_inter':'sum', 'Street':'first', 'Street_Address':'first',
                                                            'raw_area':'first', 'City':'first', 'PostalCode':'first',
                                                            'percentage_intersect':'sum'})

        # Clip tilts to account for incorrect geometries
        # Two assumptions feed into these lines:
        # 1. Rooftop tilts larger than 50 degrees are unrealistic and likely due to erroneous data. We set them to a standard tilt of 30 degrees
        # 2. PV panels are tilted in the same way as their underlying rooftop. On flat roofs, we assume a tilt angle of 30 degrees
        self.PV_intersection_gdf['Tilt'][self.PV_intersection_gdf['Tilt'] >= 50] = 30
        self.PV_intersection_gdf['Tilt'][self.PV_intersection_gdf['Tilt'] == 0] = 30

        # Calculate corrected area by considering a rooftop's tilt
        self.PV_intersection_gdf['area_tilted'] = (1 / self.PV_intersection_gdf['Tilt'].apply(math.radians).apply(math.cos)) * self.PV_intersection_gdf[
            'area_inter']

        # Group by address
        self.group_intersection_address = self.PV_intersection_gdf.groupby('Street_Address').agg({'area_inter': 'sum', 'Street_Address': 'first',
             'area_tilted': 'sum', 'Street': 'first', 'City': 'first', 'PostalCode': 'first', 'percentage_intersect': 'sum'})

        addresses = (self.group_intersection_address['Street_Address'] + ' ' + self.group_intersection_address['City']).tolist()

        coordinates = self._geocode_addresses(addresses)

        # Reset index for subsequent nearest neighbor search
        self.group_intersection_address.reset_index(drop=True, inplace=True)

        self.group_intersection_address['capacity'] = self.group_intersection_address.area_inter / 6.5

        geometry = [Point(coord[1], coord[0]) for coord in coordinates if isinstance(coord, list)]

        geometry = gpd.GeoSeries(geometry)

        self.registry = pd.concat([self.group_intersection_address, geometry], axis = 1)

        self.registry = self.registry.rename(columns={0:'geometry'})

        self.registry = gpd.GeoDataFrame(self.registry)

    def run(self):
        """
        Create an address-level PV registry by matching identified and segmented PV panels with their respective rooftop segments.
        
        Returns
        -------

        """

        self._dissolve_raw_PVs()

        self._overlay_ops()

        self._append_diff2intersect()

        self._create_registry()

        self.registry.to_file(driver='GeoJSON', filename=f"data/pv_registry/{self.county}_registry.geojson")

        









