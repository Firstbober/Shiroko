# Load config from YAML
from typing import TypedDict

import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


# Typings for the config

class GenericAPI(TypedDict):
    api_key: str


class Backend(TypedDict):
    together_ai: GenericAPI


class Config(TypedDict):
    backend: Backend


# Public API

def load_config(config_path: str) -> Config:
    with open(config_path, 'r') as config_file:
        return yaml.load(config_file, Loader)
