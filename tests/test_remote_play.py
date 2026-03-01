from src.aetherlink.core.remote_play import RemotePlay


class TestRemotePlay:
    def test_initialize(self):
        remote_play = RemotePlay()
        assert remote_play.is_initialized is False
        remote_play.initialize()
        assert remote_play.is_initialized is True

    def test_start_stop(self):
        remote_play = RemotePlay()
        remote_play.initialize()
        assert remote_play.is_running is False
        remote_play.start()
        assert remote_play.is_running is True
        remote_play.stop()
        assert remote_play.is_running is False
