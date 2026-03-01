class OpenCVCapturePlugin:
    def Initialize(self, services):
        pass

    def Start(self, profile):
        pass

    def Stop(self):
        pass

    def Shutdown(self):
        pass

    def GetCapabilities(self):
        return {
            "capture_width": 1920,
            "capture_height": 1080,
            "capture_fps": 60,
            "pixel_format_in": "NV12",
            "pixel_format_out": "BGR",
        }

    def required_entitlements(self):
        return []

    def requires_drivers(self):
        return []

    def requires_worker(self):
        return False
