from django.apps import AppConfig


class WarehouseV2Config(AppConfig):
    name = 'warehouse_v2'

    def ready(self):
        import warehouse_v2.signals
