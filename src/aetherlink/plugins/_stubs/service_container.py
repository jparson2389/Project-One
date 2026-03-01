# src/aetherlink/plugins/service_container.py

class ServiceContainer:
    def __init__(self):
        self.services = {}

    def register_service(self, service_name, service_instance):
        self.services[service_name] = service_instance

    def get_service(self, service_name):
        return self.services.get(service_name)
