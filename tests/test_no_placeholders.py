from pathlib import Path


def test_file_not_exists():
    file_path = Path('some/file.txt')
    assert not file_path.exists(), f'{file_path} still exists'
