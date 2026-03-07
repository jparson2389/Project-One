# tests/conftest.py
import sys
from pathlib import Path

import pytest


def pytest_configure():
    """Configure pytest to work with UV's environment"""
    # Add the project root to Python path so we can import modules from anywhere
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Get the project root (two levels up from tests)
    project_root = Path(__file__).resolve().parent.parent

    # Add to Python path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Make tools available (with __init__.py)
    tools_path = project_root / "tools"
    if str(tools_path) not in sys.path:
        sys.path.insert(0, str(tools_path))


@pytest.fixture
def sample_router_yaml():
    """Fixture that provides a minimal router.yaml for testing"""
    yaml_content = """
model_list:
  - model_name: architect
    litellm_params:
      model: openai/qwen/qwen2.5-coder-14b
      api_base: http://localhost:1234/v1
      api_key: lm-studio
      temperature: 0.15
      max_tokens: 4096
      context_window: 16384

  - model_name: quick-fix
    litellm_params:
      model: openai/qwen2.5-coder-7b-instruct@q8_0
      api_base: http://localhost:1234/v1
      api_key: lm-studio
      temperature: 0.1
      max_tokens: 2560
      context_window: 32768
"""
    temp_file = Path("tests/temp_router.yaml")
    temp_file.write_text(yaml_content)
    yield str(temp_file)
    temp_file.unlink()
