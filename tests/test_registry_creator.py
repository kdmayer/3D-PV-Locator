import pytest
from src.pipeline_components.registry_creator import RegistryCreator
import geopandas as gpd

"""
def test_address_registry(sample_registry_creator):

    sample_registry_creator.create_address_registry()
    actual_address_registry = gpd.read_file("/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/data/pv_registry/Essen_address_registry.geojson") 
    expected_address_registry = gpd.read_file("/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/tests/example_address_registry_Essen.geojson")
    
    assert actual_address_registry == expected_address_registry
"""

def test_double_5():
    actual = RegistryCreator.double_input(5)
    expected = 10
    
    assert actual == expected
    
    