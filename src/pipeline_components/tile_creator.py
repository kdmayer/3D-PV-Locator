# -*- coding: utf-8 -*-
"""
Created on Fri Jun 28 11:07:41 2019

@author: Kevin
"""
import numpy as np
import pickle
from shapely.geometry import Point


class TileCreator(object):

    def __init__(self, configuration, polygon):

        self.output_path = configuration['tile_coords_path']

       # Avg. earth radius in meters
        self.radius = 6371000

        # Square side length of tiles in meters
        self.side = 240

        # Bounding box coordinates for NRW, i.e. North, South, East, West
        self.N = 52.7998
        self.S = 50.0578
        self.E = 9.74158
        self.W = 5.59334

        self.polygon = polygon

    def defineTileCoords(self):

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

        with open(self.output_path,'wb') as f:

            pickle.dump(Tile_coords, f)
