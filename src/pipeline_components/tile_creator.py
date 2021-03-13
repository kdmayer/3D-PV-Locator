# -*- coding: utf-8 -*-
import numpy as np
import pickle
from shapely.geometry import Point
from pathlib import Path


class TileCreator(object):
    """
    Class to generate a list specifying all tiles within a given county by their minx, miny, maxx, maxy coordinates.

    Attributes
    ----------
    output_path : Path
        Path to the pickle file which saves the list of all tiles within the selected county.
    radius : int
        Earth radius in meters.
    side : int
        Side length in meters for the tiles.
    N : float
        Northern boundary for the tile coordinates.
    S : float
        Southern boundary for the tile coordinates.
    E : float
        Eastern boundary for the tile coordinates.
    W : float
        Western boundary for the tile coordinates.
    polygon : shapely.geometry.polygon.Polygon 
        Geo-referenced polygon geometry for the selected county within NRW.
    """

    def __init__(self, county_handler):
        """
        Parameters
        ----------
        county_handler : GeoJsonHandler
            GeoJsonHandler instance which specifies the name and the geo-referenced polygon for a selected county within North Rhine-Westphalia (NRW).
        """
        self.output_path = Path(f"data/coords/{county_handler.name}.pickle")
        self.radius = 6371000
        self.side = 240

        # Bounding box coordinates for NRW, i.e. North, South, East, West
        self.N = 52.7998
        self.S = 50.0578
        self.E = 9.74158
        self.W = 5.59334

        self.polygon = county_handler.polygon

    def defineTileCoords(self):
        """
        Spans a grid of tiles, each with a dimension 240m x 240m, over North Rhine-Westphalia and saves the tiles within the respective county by their minx, miny, maxx, maxy coordinates. 
        Only tiles where at least one corner is within the county's polygon will be saved and later downloaded.
        """

        # dlat spans a distance of 'side' meters in north-south direction:
        # 1 degree in latitude direction spans (2*np.pi*r)/360° meters
        # Hence, 'side' meters need to be divided by this quantity to obtain
        # the number of degrees which span 'side' meters in latitude (north-south) direction
        dlat = (self.side*360) / (2*np.pi*self.radius)

        Tile_coords = []

        y = self.S

        while y < self.N:

            x = self.W

            while x < self.E:

                # Center point of current image tile

                cp = Point(x,y)

                # Download 4800x4800 pixel imagery if one of the bounding box corners is inside the NRW polygon

                # Bounding box coordinates for a given image tile
                minx = x - (((self.side * 360) / (2 * np.pi * self.radius * np.cos(np.deg2rad(y))))/2)

                miny = y - dlat/2

                maxx = x + (((self.side * 360) / (2 * np.pi * self.radius * np.cos(np.deg2rad(y))))/2)

                maxy = y + dlat/2

                # Bounding box corners for a given image tile

                # Lower Left
                LL = Point(minx,miny)

                # Lower Right
                LR = Point(maxx,miny)

                # Upper Left
                UL = Point(minx,maxy)

                # Upper Right
                UR = Point(maxx, maxy)

                # If bounding box corners are within NRW polygon
                if (self.polygon.intersects(LL) | self.polygon.intersects(LR) | self.polygon.intersects(UL) | self.polygon.intersects(UR)):

                    Tile_coords.append((minx, miny, maxx, maxy))

                # Update longitude value
                x = x + ((self.side * 360) / (2 * np.pi * self.radius * np.cos(np.deg2rad(y))))

            # Update latitude value
            y = y + dlat

        with open(self.output_path, 'wb') as f:

            pickle.dump(Tile_coords, f)
