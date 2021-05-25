import pytest
import yaml
from src.pipeline_components.registry_creator import RegistryCreator

"""
To run this test suite, simply import all the necessary modules directly from the root, e.g.
from src.pipeline_components.registry_creator import RegistryCreator, and enter 
"python3 -m pytest" into the terminal
"""


@pytest.fixture
def sample_registry_creator(sample_config):
    return RegistryCreator(sample_config)
    
@pytest.fixture()
def sample_config():
    
    config_file = '/Users/kevin/Projects/Active/PV4GERFiles/pv4ger/tests/example_config.yml'
    with open(config_file, 'rb') as f:

        conf = yaml.load(f, Loader=yaml.FullLoader)
    return conf