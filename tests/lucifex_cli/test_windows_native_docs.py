from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\lucifex\\lucifex-agent\\venv\\Scripts" in doc
    assert "Get-Command lucifex        # should print C:\\Users\\<you>\\AppData\\Local\\lucifex\\lucifex-agent\\venv\\Scripts\\lucifex.exe" in doc
    assert '$lucifexBin = "$InstallDir\\venv\\Scripts"' in install
