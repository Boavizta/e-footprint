import os
import shutil

from docs_sources.doc_utils.format_tutorial_md import efootprint_tutorial_to_md, \
    format_tutorial_and_save_to_mkdocs_sourcefiles
from docs_sources.doc_utils.generate_object_reference import generate_object_reference
from efootprint.logger import logger

file_path = os.path.dirname(os.path.abspath(__file__))
mkdocs_sourcefiles = os.path.join(file_path, "..", "mkdocs_sourcefiles")
generated_mkdocs_sourcefiles = os.path.join(file_path, "..", "generated_mkdocs_sourcefiles")


def wipe_out_folder_while_keeping_file(folder_path, file_to_keep):
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)

        if item == file_to_keep:
            continue

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)  # Delete the file or symbolic link
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)  # Recursively delete the directory


logger.info("Wiping out generated_mkdocs_sourcefiles")
wipe_out_folder_while_keeping_file(generated_mkdocs_sourcefiles, file_to_keep=".gitignore")
logger.info("Converting e-footprint tutorial to markdown")
md_doc_tuto_path = efootprint_tutorial_to_md()
logger.info("Reformating markdown tutorial file and saving it to mkdocs_sourcefiles")
format_tutorial_and_save_to_mkdocs_sourcefiles(md_doc_tuto_path)
logger.info("Generating object reference")
generate_object_reference()
logger.info("Copying changelog and manually written doc files to generated_mkdocs_sourcefiles")
with open(os.path.join(file_path, "..", "..", "CHANGELOG.md"), "r") as file:
    changelog = file.read()

changelog = changelog.replace("./", "https://github.com/Boavizta/e-footprint/tree/main/")

with open(os.path.join(generated_mkdocs_sourcefiles, "Changelog.md"), "w") as file:
    file.write(changelog)

# Copy the entire directory tree
shutil.copytree(mkdocs_sourcefiles, generated_mkdocs_sourcefiles, dirs_exist_ok=True)
