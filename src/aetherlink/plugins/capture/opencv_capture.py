"""OpenCV Capture Plugin."""


class OpenCVCapturePlugin:
    """Plugin for capturing video using OpenCV."""

    def initialize(self, services):
        """Initialize the plugin."""
        pass

    def start(self, profile):
        """Start capturing."""
        pass

    def stop(self):
        """Stop capturing."""
        pass

    def shutdown(self):
        """Shutdown the plugin."""
        pass

    def get_capabilities(self):
        """Get plugin capabilities."""
        return {
            "capture_width": 1920,
            "capture_height": 1080,
            "capture_fps": 60,
            "pixel_format_in": "NV12",
            "pixel_format_out": "BGR",
        }

    def required_entitlements(self):
        """Get required entitlements."""
        return []

    def requires_drivers(self):
        """Get required drivers."""
        return []

    def requires_worker(self):
        """Check if worker is required."""
        return False
