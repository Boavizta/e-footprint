import subprocess
import os

from format_tutorial_md import file_path, mkdocs_sourcefiles_path


def format_builders_ipynb_to_md_and_save_to_mkdocs_sourcefiles(
        builders_path=os.path.join(file_path, "..", "..", "builders.ipynb")):
    subprocess.run(
        ["jupyter", "nbconvert", "--to", "markdown", builders_path], check=True)

    md_filepath = builders_path.replace("ipynb", "md")

    os.rename(md_filepath, md_filepath.replace(os.path.dirname(md_filepath), mkdocs_sourcefiles_path))


if __name__ == "__main__":
    format_builders_ipynb_to_md_and_save_to_mkdocs_sourcefiles()
