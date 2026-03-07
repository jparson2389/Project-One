import loguru
import pytest
from src.aetherlink.plugins.service_container import ServiceContainer

loguru.logger.remove()
loguru.logger.add('test.log', level='DEBUG')


def test_register_and_get():
    container = ServiceContainer()
    service_instance = object()
    container.register('my_service', service_instance)
    assert container.get('my_service') is service_instance


def test_missing_key():
    container = ServiceContainer()
    with pytest.raises(KeyError):
        container.get('non_existent_service')
