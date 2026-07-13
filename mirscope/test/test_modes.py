"""Integration tests for the analysis modes, focused on --out handling."""
from mirscope.modes.macro import MacroMode


def _write_reference(folder):
    folder.mkdir()
    (folder / "mirna_Homo_sapiens.fasta").write_text(">hsa-1\nUGAGAUUCUUGAUGAU\n")
    (folder / "mirna_Mus_musculus.fasta").write_text(">mmu-1\nUGAGAUUCUUGAUGAU\n")


def test_macro_creates_output_dir_and_files(tmp_path):
    data = tmp_path / "data"
    _write_reference(data)
    out = tmp_path / "results"

    MacroMode().run(str(data), None, str(out))

    assert out.is_dir()
    assert (out / "output_mode1_macro_detailed.xlsx").exists()
    assert (out / "output_mode1_matrix_upset.xlsx").exists()
    assert (out / "results_mode1_macro.png").exists()


def test_macro_creates_nested_output_dir(tmp_path):
    data = tmp_path / "data"
    _write_reference(data)
    out = tmp_path / "nested" / "run1"

    MacroMode().run(str(data), None, str(out))

    assert (out / "output_mode1_macro_detailed.xlsx").exists()
