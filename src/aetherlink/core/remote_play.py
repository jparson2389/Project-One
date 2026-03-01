class RemotePlay:
    def __init__(self):
        self.is_initialized = False
        self.is_running = False

    def initialize(self) -> None:
        # Simulate initialization logic
        self.is_initialized = True

    def start(self) -> None:
        if not self.is_initialized:
            raise RuntimeError('RemotePlay is not initialized')
        # Simulate starting logic
        self.is_running = True

    def stop(self) -> None:
        if not self.is_running:
            raise RuntimeError('RemotePlay is not running')
        # Simulate stopping logic
        self.is_running = False
