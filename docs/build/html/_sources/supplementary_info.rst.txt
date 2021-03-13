Supplementary Information
===================

**PV4GER/data/nrw_county_data/**
    Directory which contains a GeoJSON that specifies the administrative boundaries for all counties within North Rhine-Westphalia (NRW).

**PV4GER/data/nrw_rooftop_data/**
    Directory which contains one GeoJSON per county. The GeoJSON specifies all the rooftop information for your selected county, e.g. rooftop orientations, tilts, and geo-referenced polygons. **You need to download the respective .GeoJSON for your chosen county from our public S3 bucket as described in the README.md**.

**PV4GER/data/pv_database/**
    Directory which contains a .csv for each analyzed county, specifying all detected PV panels by their tile ID (minx, miny, maxx, maxy coordinates), their image ID (upper left corner), and their actual geo-referenced polygon terms of latitude and longitude.

**PV4GER/data/pv_registry/**
    Directory which contains the actual PV registry in .GeoJSON format for each analyzed county.

