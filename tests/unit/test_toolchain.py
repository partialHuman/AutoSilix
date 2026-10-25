"""Unit tests for toolchain detection and environment inventory."""

from autosilix.toolchain import ToolchainDetector, ToolInfo


def test_inspect_tool_known():
    info = ToolchainDetector.inspect_tool("git")
    assert isinstance(info, ToolInfo)
    assert info.name == "git"
    assert info.category == "vcs"


def test_inspect_tool_nonexistent():
    info = ToolchainDetector.inspect_tool("nonexistent_tool_12345")
    assert info.available is False
    assert info.path is None


def test_get_inventory():
    inv = ToolchainDetector.get_inventory()
    assert "git" in inv
    assert "iverilog" in inv
    assert "yosys" in inv
    assert "openroad" in inv


def test_get_environment_info():
    env = ToolchainDetector.get_environment_info()
    assert "os" in env
    assert "python_version" in env
    assert "tools" in env
    assert isinstance(env["tools"], dict)
