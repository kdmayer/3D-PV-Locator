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
from typing import List, Optional, Tuple


class RawSolarDatabase:
    def from_csv(self, file_path: Path):
        """
        Load raw PV polygons detected during the previous pipeline step from csv

        Parameters
        ----------
        file_path: Path
            Path to file where all detected PV polygons from the tile processing step are stored.

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoPandas.GeoDataFrame specifying all raw PV polygons detected during the previous pipeline step within a
            given county.
        """

        # Load PV database file and convert it to a Geopandas.GeoDataFrame with EPSG:4326 as the coordinate reference system
        solar_db = pd.read_csv(
            file_path,
            sep=";",
            header=None,
            names=["Current_Tile_240", "UL_Image_16", "geometry"],
        )

        solar_db["geometry"] = solar_db["geometry"].apply(wkt.loads)

        solar_db = gpd.GeoDataFrame(solar_db, geometry="geometry")
        solar_db.crs = {"init": "epsg:4326"}
        solar_db["class"] = int(1)
        return solar_db[["class", "geometry"]]


class RegistryCreator:
    """
    Creates an address-level and rooftop-level PV registry for the specified county by bringing together the
    information obtained from the tile processing step with the county's 3D rooftop data.

    Attributes
    ----------
    county: str
        Name of the county for which the enrichted automated PV registry is created.
    raw_PV_polygons_gdf: GeoPandas.GeoDataFrame
        Contains all the identified and segmented PV panels within a given county based on the results from the previous tile processing step.
    rooftop_gdf: GeoPandas.GeoDataFrame
        Contains all the rooftop information such as a rooftop's tilt, its azimuth, and its geo-referenced polygon derived from openNRW's 3D building data.
    bing_key: str
        Your Bing API key which is needed to reverse geocode lat, lon values into actual street addresses.
    corrected_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
        GeoDataFrame with preprocessed PV polygons matched to their respective rooftop segments
    """

    def __init__(self, configuration):
        """
        Parameters
        ----------
        configuration: dict
            The configuration based on config.yml in dict format.
        """

        self.county = configuration.get("county4analysis")
        # replace with f"/data/pv_database/{self.county}_PV_db.csv"
        self.raw_PV_polygons_gdf = RawSolarDatabase().from_csv(
            Path(
                f"/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/data/pv_database/{self.county}_PV_db.csv"
            )
        )

        # replace with Path(f"{configuration['rooftop_data_dir']}/{self.county}_Clipped.geojson")
        self.rooftop_gdf = gpd.read_file(
            Path(
                f"/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/{configuration['rooftop_data_dir']}"
                f"/{self.county}_Clipped.geojson"
            )
        )
        self.rooftop_gdf.crs = {"init": "epsg:4326"}

        self.bing_key = configuration["bing_key"]

        self.corrected_PV_installations_on_rooftop = self.preprocess_raw_pv_polygons(
            self.raw_PV_polygons_gdf, self.rooftop_gdf
        )

    def preprocess_raw_pv_polygons(
        self, raw_PV_polygons_gdf: gpd.GeoDataFrame, rooftop_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Preprocessing the raw PV polygons detected during the previous pipeline step.

        Parameters
        ----------
        raw_PV_polygons_gdf: GeoPandas.GeoDataFrame
            GeoPandas.GeoDataFrame consisting off all detected PV polygons from the previous pipeline step.
        rooftop_gdf: GeoPandas.GeoDataFrame
            GeoPandas.GeoDataFrame specifying all rooftop geometries and attributes within the given county

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoPandas.GeoDataFrame specifying all rooftop intersected PV polygons within a given county
            together with the corresponding rooftop attributes and the PV system area corrected by the rooftop's tilt.
        """

        raw_PV_installations_gdf = (
            self.aggregate_raw_PV_polygons_to_raw_PV_installations(raw_PV_polygons_gdf)
        )

        [
            raw_PV_installations_on_rooftop,
            raw_PV_installations_off_rooftop,
        ] = self.overlay_raw_PV_installations_and_rooftops(
            raw_PV_installations_gdf, rooftop_gdf
        )

        raw_overhanging_PV_installations = (
            self.identify_raw_overhanging_PV_installations(
                raw_PV_installations_off_rooftop
            )
        )

        raw_overhanging_PV_installations = (
            self.filter_raw_overhanging_PV_installations_by_area(
                raw_overhanging_PV_installations,
                raw_PV_installations_on_rooftop,
            )
        )

        raw_PV_installations_on_rooftop = (
            self.append_raw_overhanging_PV_installations_to_intersected_installations(
                raw_overhanging_PV_installations,
                raw_PV_installations_on_rooftop,
            )
        )

        # Create street address column
        raw_PV_installations_on_rooftop["Street_Address"] = (
            raw_PV_installations_on_rooftop["Street"]
            + " "
            + raw_PV_installations_on_rooftop["StreetNumb"]
            + ", "
            + raw_PV_installations_on_rooftop["PostalCode"]
            + ", "
            + raw_PV_installations_on_rooftop["City"]
        )

        raw_PV_installations_on_rooftop = self.remove_erroneous_pv_polygons(
            raw_PV_installations_on_rooftop
        )

        corrected_PV_installations_on_rooftop = self.adjust_detected_pv_area_by_tilt(
            raw_PV_installations_on_rooftop
        )

        return corrected_PV_installations_on_rooftop

    def aggregate_raw_PV_polygons_to_raw_PV_installations(
        self, raw_PV_polygons_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Aggregate raw PV polygons belonging to the same PV installation. Raw refers to the fact that the PV area is
        not corrected by the tilt angle. For each PV installation, we compute its raw area and a unique identifier.

        Parameters
        ----------
        raw_PV_polygons_gdf : GeoPandas.GeoDataFrame
            GeoDataFrame which contains all the raw PV polygons which have been detected during the previous pipeline step.
        Returns
        -------
        GeoPandas.GeoDataFrame
           GeoDataFrame with dissolved PV polygon geometries.
        """

        # Buffer polygons, i.e. overwrite the original polygons with their buffered versions
        # Based on our experience, the buffer value should be within [1e-6, 1e-8] degrees
        raw_PV_polygons_gdf["geometry"] = raw_PV_polygons_gdf["geometry"].buffer(1e-6)

        # Dissolve, i.e. aggregate, all PV polygons into one Multipolygon
        raw_PV_polygons_gdf = raw_PV_polygons_gdf.dissolve(by="class")

        # Explode multi-part geometries into multiple single geometries
        raw_PV_installations_gdf = (
            raw_PV_polygons_gdf.explode().reset_index().drop(columns=["level_1"])
        )

        # Compute the raw area for each pv installation
        raw_PV_installations_gdf["raw_area"] = (
            raw_PV_installations_gdf["geometry"].to_crs(epsg=5243).area
        )

        # Create a unique identifier for each pv installation
        raw_PV_installations_gdf["identifier"] = raw_PV_installations_gdf.index.map(
            lambda id: "polygon_" + str(id)
        )

        return raw_PV_installations_gdf

    def overlay_raw_PV_installations_and_rooftops(
        self,
        raw_PV_installations_gdf: gpd.GeoDataFrame = None,
        rooftop_gdf: gpd.GeoDataFrame = None,
    ) -> List[gpd.GeoDataFrame]:
        """
        Overlay PV polygon geometries with rooftop geometries.

        Parameters
        ----------
        raw_PV_installations_gdf : GeoPandas.GeoDataFrame
            GeoDataFrame with dissolved PV polygon geometries.
        rooftop_gdf : GeoPandas.GeoDataFrame
            GeoDataFrame specifying all rooftop geometries in a given county.
        Returns
        -------
        List[GeoPandas.GeoDataFrame]
            The first element specifies PV polygons intersected with rooftop geometries, while the second element
            specifies PV polygons which do not intersect with rooftop geometries
        """

        # Intersect PV panels and rooftop polygons to enrich all the PV polygons with the attributes of their respective rooftop polygon
        raw_PV_installations_on_rooftop = gpd.overlay(
            raw_PV_installations_gdf, rooftop_gdf, how="intersection"
        )

        raw_PV_installations_on_rooftop["area_inter"] = (
            raw_PV_installations_on_rooftop["geometry"].to_crs(epsg=5243).area
        )

        # PV polygons which are not on rooftops. This includes free-standing PV units and geometries overhanging from rooftops
        raw_PV_installations_off_rooftop = gpd.overlay(
            raw_PV_installations_gdf, rooftop_gdf, how="difference"
        )

        raw_PV_installations_off_rooftop["area_diff"] = (
            raw_PV_installations_off_rooftop["geometry"].to_crs(epsg=5243).area
        )

        return [raw_PV_installations_on_rooftop, raw_PV_installations_off_rooftop]

    def _ckdnearest(
        self, gdA: gpd.GeoDataFrame = None, gdB: gpd.GeoDataFrame = None
    ) -> gpd.GeoDataFrame:
        """
        Identifies the nearest points of GeoPandas.DataFrame gdB in GeoPandas.DataFrame gdA. Indices need to be resorted before using this function.

        Parameters
        ----------
        gdA : GeoPandas.GeoDataFrame
            GeoDataFrame which contains a column specifying shapely.geometry.Point objects for the centroids of the
            overhanging PV polygons
        gdB : GeoPandas.GeoDataFrame
            GeoDataFrame which contains a column specifying shapely.geometry.Point objects for the centroids of the
            intersected PV polygons
        Returns
        -------
        GeoPandas.GeoDataFrame
            Concatenated GeoPandas.GeoDataFrame containing all columns of both GeoDataFrames excluding gdB's
            geometry, i.e. the centroid of the intersected PV polygons, plus distance in degrees.
        """

        # List specifying the centroid coordinates of the overhanging PV polygons
        nA = np.array(list(zip(gdA.geometry.x, gdA.geometry.y)))

        # List specifying the centroid coordinates of the intersected PV polygons
        nB = np.array(list(zip(gdB.geometry.x, gdB.geometry.y)))

        btree = cKDTree(nB)

        # idx lists the index of the nearest neighbor in nB for each centroid in nA
        # dist specifies the respective distance between the nearest neighbors in degrees
        dist, idx = btree.query(nA, k=1)

        gdf = pd.concat(
            [
                gdA.reset_index(drop=True),
                gdB.loc[idx, gdB.columns != "geometry"].reset_index(drop=True),
                pd.Series(dist, name="dist_in_degrees"),
            ],
            axis=1,
        )

        # GeoDataFrame adding all the attributes of the nearest intersected PV polygon to the overhanging PV polygons
        return gpd.GeoDataFrame(gdf)

    def calculate_distance_in_meters_between_raw_overhanging_pv_installation_centroid_and_nearest_intersected_installation_centroid(
        self,
        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data: gpd.GeoDataFrame = None,
    ):
        """
        Calculate the distance in meters between the centroid of the overhanging PV polygon, here points_no_data,
        and the PV polygon centroid which is intersected with a rooftop polygon, here address_points

        Parameters
        ----------
        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data: GeoPandas.GeoDataFrame
            GeoDataFrame where overhanging PV installations have been enriched with the attributes of the closest
            rooftop

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame where overhanging PV installations have been enriched with the attributes of the closest
            rooftop with an additional attribute which specifies the distance between the centroid of the overhanging PV polygon and the centroid of the intersected PV polygon in meters
        """

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "helper_x"
        ] = gpd.GeoSeries(
            raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                "centroid_intersect"
            ]
        ).x

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "helper_y"
        ] = gpd.GeoSeries(
            raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                "centroid_intersect"
            ]
        ).y

        # Centroid coordinates of intersected pv polygons
        address_points = list(
            zip(
                raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                    "helper_x"
                ],
                raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                    "helper_y"
                ],
            )
        )

        # Centroid coordinates of overhanging pv polygons
        points_no_data = list(
            zip(
                raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                    "geometry"
                ].x,
                raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                    "geometry"
                ].y,
            )
        )

        dist = [
            geopy.distance.geodesic(address, no_data).m
            for address, no_data in zip(address_points, points_no_data)
        ]

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "dist_in_meters"
        ] = pd.Series(dist)

        return raw_overhanging_pv_installations_enriched_with_closest_rooftop_data

    def identify_raw_overhanging_PV_installations(
        self,
        raw_PV_installations_off_rooftop: gpd.GeoDataFrame = None,
    ) -> gpd.GeoDataFrame:
        """
        Remove PV systems from raw_PV_installations_off_rooftop which are free-standing, i.e. only use the ones
        belonging, i.e. bordering, to a rooftop.

        Parameters
        ----------
        raw_PV_installations_off_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which do not intersect with a rooftop geometry. This
            includes free-standing PV systems and PV polygons which border to a rooftop, but couldn't be matched to
            that rooftop geometry initially.

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which border to a rooftop geometry but are not yet
            matched with the attributes of the correspoding rooftop. All free-standing PV
            system units, i.e. those which are not mounted on a rooftop, have been removed.
        """

        # Free-standing units can be identified by the fact that their raw_area == area_diff
        raw_PV_installations_off_rooftop["checker"] = (
            raw_PV_installations_off_rooftop.raw_area
            - raw_PV_installations_off_rooftop.area_diff
        )

        raw_overhanging_PV_installations = raw_PV_installations_off_rooftop[
            raw_PV_installations_off_rooftop["checker"] > 0
        ]

        raw_overhanging_PV_installations = raw_overhanging_PV_installations[
            ["area_diff", "identifier", "geometry"]
        ]

        # Remove nan values which arise from corrupted rooftop geometries (rare)
        raw_overhanging_PV_installations = raw_overhanging_PV_installations[
            ~raw_overhanging_PV_installations.identifier.isnull()
        ]

        # Save the shape of the overhanging PV system polygon
        raw_overhanging_PV_installations[
            "geometry_overhanging_polygon"
        ] = raw_overhanging_PV_installations["geometry"]

        # Compute centroid of overhanging PV system polygons
        raw_overhanging_PV_installations["geometry"] = raw_overhanging_PV_installations[
            "geometry"
        ].centroid

        return raw_overhanging_PV_installations

    def filter_raw_overhanging_PV_installations_by_area(
        self,
        raw_overhanging_PV_installations: gpd.GeoDataFrame = None,
        raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None,
    ) -> gpd.GeoDataFrame:
        """
        Only overhanging PV polygons which are larger than 1 sqm in area will be kept.

        Parameters
        ----------
        raw_overhanging_PV_installations: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which border to a rooftop geometry.
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which are intersected with a rooftop geometry

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame where overhanging PV installations have been filtered to contain only
            those which border to a rooftop and are larger than 1 sqm in area
        """

        # Select all the PV polygon IDs which have been successfully intersected with a rooftop
        rooftop_pv_ids = raw_PV_installations_on_rooftop.identifier.unique().tolist()

        # Select all the overhanging PV polygons whose identifier matches with one of the intersected solar panels
        # mounted on a rooftop
        raw_overhanging_PV_installations = raw_overhanging_PV_installations[
            raw_overhanging_PV_installations.identifier.isin(rooftop_pv_ids)
        ]

        # Only consider cut-off geometries larger than 1 sqm
        raw_overhanging_PV_installations = raw_overhanging_PV_installations[
            raw_overhanging_PV_installations["area_diff"] > 1.0
        ]

        return raw_overhanging_PV_installations

    def enrich_raw_overhanging_pv_installations_with_closest_rooftop_attributes(
        self,
        raw_overhanging_PV_installations: gpd.GeoDataFrame = None,
        raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None,
    ) -> gpd.GeoDataFrame:
        """
        PV polygons which do not intersect with a rooftop polygon, although they do border to a rooftop, are matched to
        their nearest rooftop geometry

        Parameters
        ----------
        raw_overhanging_PV_installations: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which border to a rooftop, but are not intersected with
            a rooftop geometry
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which are intersected with a rooftop geometry

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame where overhanging PV installations have been enriched with the attributes of the closest
            rooftop
        """

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data = (
            self._ckdnearest(
                raw_overhanging_PV_installations,
                raw_PV_installations_on_rooftop,
            )
        )

        # Check if the identifier of the intersected polygon is the same as the identifier of the overhanging polygon
        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "checker"
        ] = (
            raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                "identifier_diff"
            ]
            == raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                "identifier"
            ]
        )

        # Calculate the distance in meters between the centroid of the overhanging PV polygon and the centroid of the
        # PV polygon which is intersected with a rooftop polygon
        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data = self.calculate_distance_in_meters_between_raw_overhanging_pv_installation_centroid_and_nearest_intersected_installation_centroid(
            raw_overhanging_pv_installations_enriched_with_closest_rooftop_data
        )

        # The value for the area of the intersected PV installation is updated by the area of the overhanging PV polygon
        # in order to aggregate the areas for a given rooftop later
        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "area_inter"
        ] = raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
            "area_diff"
        ]

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data = (
            raw_overhanging_pv_installations_enriched_with_closest_rooftop_data[
                [
                    "raw_area",
                    "identifier",
                    "Area",
                    "Azimuth",
                    "Building_I",
                    "City",
                    "PostalCode",
                    "RoofTopID",
                    "RooftopTyp",
                    "Street",
                    "StreetNumb",
                    "Tilt",
                    "area_inter",
                    "geometry_overhanging_polygon",
                ]
            ]
        )

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data.rename(
            columns={"geometry_overhanging_polygon": "geometry"}, inplace=True
        )

        return raw_overhanging_pv_installations_enriched_with_closest_rooftop_data

    def append_raw_overhanging_PV_installations_to_intersected_installations(
        self,
        raw_overhanging_PV_installations: gpd.GeoDataFrame = None,
        raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None,
    ) -> gpd.GeoDataFrame:
        """
        PV polygons which do not intersect with a rooftop polygon, although they do border to a rooftop, are matched to
        their nearest rooftop geometry and appended to the GeoDataFrame listing all rooftop PV polygons

        Parameters
        ----------
        raw_overhanging_PV_installations: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which border to a rooftop, but are not intersected with
            a rooftop geometry
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which specifies all the PV polygons which are intersected with a rooftop geometry

        Returns
        -------
        GeoPandas.GeoDataFrame
            GeoDataFrame where overhanging PV installations have been enriched with the attributes of the closest
            rooftop and appended to raw_PV_installations_on_rooftop
        """

        # IMPORTANT: if ckdnearest is used always reset_index before
        raw_overhanging_PV_installations = raw_overhanging_PV_installations.reset_index(
            drop=True
        )

        raw_overhanging_PV_installations.rename(
            columns={"identifier": "identifier_diff"}, inplace=True
        )

        # Extract centroid from intersected PV polygons while preserving their polygon geometry
        raw_PV_installations_on_rooftop[
            "geometry_intersected_polygon"
        ] = raw_PV_installations_on_rooftop["geometry"]
        raw_PV_installations_on_rooftop["geometry"] = raw_PV_installations_on_rooftop[
            "geometry"
        ].centroid
        raw_PV_installations_on_rooftop[
            "centroid_intersect"
        ] = raw_PV_installations_on_rooftop["geometry"]

        raw_overhanging_pv_installations_enriched_with_closest_rooftop_data = self.enrich_raw_overhanging_pv_installations_with_closest_rooftop_attributes(
            raw_overhanging_PV_installations, raw_PV_installations_on_rooftop
        )

        raw_PV_installations_on_rooftop.geometry = (
            raw_PV_installations_on_rooftop.geometry_intersected_polygon
        )

        raw_PV_installations_on_rooftop = raw_PV_installations_on_rooftop[
            [
                "raw_area",
                "identifier",
                "Area",
                "Azimuth",
                "Building_I",
                "City",
                "PostalCode",
                "RoofTopID",
                "RooftopTyp",
                "Street",
                "StreetNumb",
                "Tilt",
                "area_inter",
                "geometry",
            ]
        ]

        # Append the dataframe of all raw overhanging PV installations, enriched with the
        # rooftop attributes of their nearest rooftop, to the dataframe of all intersected PV installations
        # Note 1: Attributes starting with capital letters specify rooftop attributes.
        # Note 2: The geometry of the overhanging PV installations is not yet dissolved with the geometry of the
        # intersected PV installations
        raw_PV_installations_on_rooftop = gpd.GeoDataFrame(
            raw_PV_installations_on_rooftop.append(
                raw_overhanging_pv_installations_enriched_with_closest_rooftop_data
            )
        ).reset_index(drop=True)

        return raw_PV_installations_on_rooftop

    def remove_erroneous_pv_polygons(
        self, raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None
    ) -> gpd.GeoDataFrame:
        """
        Removes PV polygons whose aggregated intersected area is larger than their original raw area

        Parameters
        ----------
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which must contain the columns "area_inter", "raw_area", and "identifier"
        Returns
        -------
        GeoPandas.GeoDataFrame
            Input GeoDataFrame where erroneous PV polygons have been removed
        """

        # Compute share of raw area that the intersected pv polygon covers
        raw_PV_installations_on_rooftop["percentage_intersect"] = (
            raw_PV_installations_on_rooftop["area_inter"]
            / raw_PV_installations_on_rooftop["raw_area"]
        )

        # Group intersection by polygon identifier and sum percentage
        group_intersection_id = raw_PV_installations_on_rooftop.groupby(
            "identifier"
        ).agg(
            {
                "area_inter": "sum",
                "Street": "first",
                "Street_Address": "first",
                "raw_area": "first",
                "City": "first",
                "PostalCode": "first",
                "percentage_intersect": "sum",
            }
        )

        # Find erroneous polygons whose area after intersection is larger than their original (raw) area
        polygone = group_intersection_id[
            group_intersection_id["percentage_intersect"] > 1.1
        ].index.tolist()

        # Filter out erroneous polygons identified above and all their respective sub-parts
        raw_PV_installations_on_rooftop = raw_PV_installations_on_rooftop.drop(
            raw_PV_installations_on_rooftop.index[
                (raw_PV_installations_on_rooftop["identifier"].isin(polygone))
                & (raw_PV_installations_on_rooftop["percentage_intersect"] < 1)
            ]
        )

        # Drop duplicate identifiers for erroneous polygons
        raw_PV_installations_on_rooftop = raw_PV_installations_on_rooftop.drop(
            raw_PV_installations_on_rooftop.index[
                (raw_PV_installations_on_rooftop["identifier"].isin(polygone))
                & (raw_PV_installations_on_rooftop["identifier"].duplicated())
            ]
        )

        return raw_PV_installations_on_rooftop

    def clip_incorrect_tilts(
        self, raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None
    ) -> gpd.GeoDataFrame:
        """
        Adjusts tilts which are determined to be unreasonable to standard values

        Parameters
        ----------
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which must contain the column "Tilt"
        Returns
        -------
        GeoPandas.GeoDataFrame
            Input GeoDataFrame where values in the "Tilt" are adjusted to standard values if they are deemed to be
            incorrect
        """

        # Two assumptions feed into these lines:
        # 1. Rooftop tilts larger than 50 degrees are unrealistic and likely due to erroneous data. We set them to a
        # standard tilt of 30 degrees
        # 2. PV panels are tilted in the same way as their underlying rooftop. On flat roofs, we assume a tilt angle
        # of 30 degrees
        raw_PV_installations_on_rooftop["Tilt"][
            raw_PV_installations_on_rooftop["Tilt"] >= 50
        ] = 30
        raw_PV_installations_on_rooftop["Tilt"][
            raw_PV_installations_on_rooftop["Tilt"] == 0
        ] = 30

        return raw_PV_installations_on_rooftop

    def adjust_detected_pv_area_by_tilt(
        self, raw_PV_installations_on_rooftop: gpd.GeoDataFrame = None
    ) -> gpd.GeoDataFrame:
        """
        Adjusts detected PV area by considering the rooftop's tilt

        Parameters
        ----------
        raw_PV_installations_on_rooftop: GeoPandas.GeoDataFrame
            GeoDataFrame which must contain the columns "Tilt" and "area_inter"
        Returns
        -------
        GeoPandas.GeoDataFrame
            Input GeoDataFrame extended by an additional column named "area_tilted" which adjusts
            the detected PV area by considering the rooftop's tilt
        """

        raw_PV_installations_on_rooftop = self.clip_incorrect_tilts(
            raw_PV_installations_on_rooftop
        )

        # Calculate corrected area by considering a rooftop's tilt
        raw_PV_installations_on_rooftop["area_tilted"] = (
            1
            / raw_PV_installations_on_rooftop["Tilt"]
            .apply(math.radians)
            .apply(math.cos)
        ) * raw_PV_installations_on_rooftop["area_inter"]

        return raw_PV_installations_on_rooftop

    def _geocode_addresses(self, addresses: List[str]) -> List[Tuple[float, float]]:
        """
        Helper function to geocode a list of addresses

        Parameters
        ----------
        addresses: list
            list of all street addresses to be geocoded into latitude and longitude format
        Returns
        -------
        coordinates: list
            list of all geocoded street addresses
        """

        coordinates = []
        counter = 0

        for i in range(len(addresses)):

            counter += 1
            print(f"Geocode address {addresses[i]} at {counter}/{len(addresses)}")

            # Apply some sleep to ensure to be below 50 requests per second
            time.sleep(0.1)
            address = addresses[i]
            # g = geocoder.bing(address, key=self.bing_key)
            g = geocoder.osm(address)

            if g.status == "OK":

                coords = g.latlng
                coordinates.append(coords)

            else:

                print("status: {}".format(g.status))
                coordinates.append(",")

        return coordinates

    def calculate_pv_capacity(
        self, registry: gpd.GeoDataFrame = None
    ) -> gpd.GeoDataFrame:
        """
        Converts the detected PV area into a PV capacity estimate

        Parameters
        ----------
        registry: GeoPandas.GeoDataFrame
            GeoDataFrame which must contain the columns "area_inter" and "area_tilted"
        Returns
        -------
        GeoPandas.GeoDataFrame
            Input GeoDataFrame extended by two additional columns named "capacity_not_tilted_area" and
            "capacity_tilted_area"
        """

        # We assume that 6.5 sqm of PV area are needed to produce 1 kWp
        registry["capacity_not_tilted_area"] = registry.area_inter / 6.5

        registry["capacity_tilted_area"] = registry.area_tilted / 6.5

        return registry

    def create_registry_for_PV_installations(self):
        """
        Create an address-level and rooftop-level PV registry by grouping identified and segmented PV panels
        by their address or rooftop id, respectively.
        """

        # Group by rooftop ID
        self.rooftop_registry = self.corrected_PV_installations_on_rooftop.dissolve(
            by="RoofTopID",
            aggfunc={
                "Azimuth": "first",
                "Tilt": "first",
                "area_inter": "sum",
                "area_tilted": "sum",
                "RoofTopID": "first",
                "Street": "first",
                "City": "first",
                "PostalCode": "first",
                "Street_Address": "first",
            },
        )

        # Group by street address
        self.address_registry = self.corrected_PV_installations_on_rooftop.dissolve(
            by="Street_Address",
            aggfunc={
                "area_inter": "sum",
                "area_tilted": "sum",
                "Street": "first",
                "City": "first",
                "PostalCode": "first",
                "Street_Address": "first",
            },
        )

        # Reset index for subsequent nearest neighbor search
        self.rooftop_registry.reset_index(drop=True, inplace=True)
        self.address_registry.reset_index(drop=True, inplace=True)

        """
        # You cannot save two columns with shapely objects to a geojson file
        addresses = (self.address_registry["Street_Address"]).tolist()

        coordinates = self._geocode_addresses(addresses)

        street_address_coords = gpd.GeoSeries(
            [
                Point(coord[1], coord[0])
                for coord in coordinates
                if isinstance(coord, list)
            ]
        )

        self.address_registry = pd.concat(
            [self.address_registry, street_address_coords], axis=1
        )

        self.address_registry = self.address_registry.rename(
            columns={0: "geocoded_street_address"}
        )
        
        """

        self.rooftop_registry = self.calculate_pv_capacity(self.rooftop_registry)

        self.address_registry = self.calculate_pv_capacity(self.address_registry)

        self.rooftop_registry.to_file(
            driver="GeoJSON",
            filename=f"/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/data/pv_registry/{self.county}_rooftop_registry.geojson",
        )

        self.address_registry.to_file(
            driver="GeoJSON",
            filename=f"/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/data/pv_registry/{self.county}_address_registry.geojson",
        )


if __name__ == "__main__":

    import yaml

    config_file = "/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/config.yml"

    with open(config_file, "rb") as f:

        conf = yaml.load(f, Loader=yaml.FullLoader)

    RegistryCreator(conf).create_registry_for_PV_installations()
