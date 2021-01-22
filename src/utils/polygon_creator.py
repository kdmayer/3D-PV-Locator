from shapely.geometry import Polygon
import numpy as np
import rasterio.features as raster
from fiona.crs import from_epsg
import geopandas as gpd

class PolygonCreator():

    def __init__(self, size, side, earth_radius, dlat):

        self.size = size
        self.side = side
        self.earth_radius = earth_radius
        # dlat spans a distance of self.side meters in north-south direction
        self.dlat = dlat
        self.epsg = 4326

    def _deltapx2latlon(self, px_distance):

        dist_px_x, dist_px_y = px_distance
        lat_max, lon_min = self.upper_left_coords
        lat_new = lat_max - (self.dlat * (dist_px_y/self.size))
        lon_new = lon_min + (((self.side * 360) / (2 * np.pi * self.earth_radius * np.cos(np.deg2rad(lat_new))))) * (dist_px_x/self.size)

        return (lat_new, lon_new)

    def _polygon2latlon(self, poly_exterior_coords):

        poly_latlon = []
        for px_distance in poly_exterior_coords:
            poly_latlon.append(self._deltapx2latlon(px_distance))
        poly_latlon = Polygon(poly_latlon)

        return poly_latlon

    def mask2polygon(self, upper_left_coords, mask):

        self.upper_left_coords = upper_left_coords

        geos = gpd.GeoDataFrame()
        geos['class'] = None
        geos['geometry'] = None
        for idx, (shape, value) in enumerate(raster.shapes(mask)):
            polygon = Polygon(shape["coordinates"][0])
            poly_exterior_coords = list(polygon.exterior.coords)
            polygon_latlon = self._polygon2latlon(poly_exterior_coords)
            geos.loc[idx, 'class'] = int(value)
            geos.loc[idx, 'geometry'] = polygon_latlon

        # Set projection for a GeoSeries so geopandas knows how to interpret the coordinates in the geometry column
        # Read docs at: https://geopandas.org/projections.html
        if geos['geometry'].crs == None:
            geos['geometry'].set_crs(epsg=self.epsg, inplace=True)

        # Set projection for the GeoDataFrame
        if geos.crs == None:
            geos.to_crs(epsg=self.epsg, inplace=True)

        return geos