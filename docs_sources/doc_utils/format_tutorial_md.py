import os
import subprocess
import shutil

from efootprint.logger import logger


doc_utils_path = os.path.dirname(os.path.abspath(__file__))
efootprint_repo_path = os.path.join(doc_utils_path, "..", "..")
efootprint_tutorial_path = os.path.join(efootprint_repo_path, "tutorial.ipynb")
generated_mkdocs_sourcefiles_path = os.path.join(doc_utils_path, "..", "generated_mkdocs_sourcefiles")


def format_tutorial_and_save_to_mkdocs_sourcefiles(tutorial_doc_path):
    with open(tutorial_doc_path.replace("ipynb", "md"), "r") as file:
        tutorial = file.read()

    tutorial_reformated = tutorial.replace("```python\n\n```", "")

    tutorial_reformated = tutorial_reformated.replace(
        'print("placeholder")\n```\n\n    placeholder',
        '```\n--8<-- "docs_sources/generated_mkdocs_sourcefiles/System footprints.html"')

    for html_file in ["object_relationships_graph.html", "object_relationships_graph_with_jobs.html",
                      "device_population_fab_footprint_calculus_graph.html"]:
        tutorial_reformated = tutorial_reformated.replace(
            f'    {html_file}',
            f'--8<-- "docs_sources/generated_mkdocs_sourcefiles/{html_file}"'
        )

    tutorial_reformated = tutorial_reformated.replace("\n\n    202", "    202").replace("```    202", "```\n\n    202")

    tutorial_reformated = tutorial_reformated.replace("notebook=False", "notebook=True")

    images_path = tutorial_doc_path.replace(".ipynb", "_files")
    tutorial_image_dirname = "tutorial_images"
    tutorial_images_dir = os.path.join(generated_mkdocs_sourcefiles_path, tutorial_image_dirname)
    if not os.path.exists(tutorial_images_dir):
        os.makedirs(tutorial_images_dir)
    for image in os.listdir(images_path):
        shutil.copy(os.path.join(images_path, image), os.path.join(tutorial_images_dir, image))

    tutorial_reformated = tutorial_reformated.replace("docs_tutorial.nbconvert_files", tutorial_image_dirname)

    with open(os.path.join(generated_mkdocs_sourcefiles_path, "tutorial.md"), "w") as file:
        file.write(tutorial_reformated)


def efootprint_tutorial_to_md():
    with open(efootprint_tutorial_path, "r") as file:
        tutorial_content = file.read()

    tutorial_content = tutorial_content.replace("notebook=True", "notebook=False").replace(
        '"system.plot_footprints_by_category_and_object(\\"System footprints.html\\")"',
        '"system.plot_footprints_by_category_and_object(\\"System footprints.html\\")\\n",\n"print(\\"placeholder\\")"')

    docs_tutorial_path = os.path.join(doc_utils_path, "docs_tutorial.ipynb")
    with open(docs_tutorial_path, "w") as file:
        file.write(tutorial_content)

    try:
        subprocess.run(["jupyter", "nbconvert", "--to", "notebook", "--execute", docs_tutorial_path], check=True)
    except subprocess.CalledProcessError:
        raise ProcessLookupError(
            "Couldn’t run the tutorial notebook, possibly because the kernel name saved in the ipynb file doesn’t match"
            " any of your kernel names. Please run the notebook with Jupyter notebook and try again.")

    for file in os.listdir(doc_utils_path):
        if file.endswith("html"):
            logger.debug(f"moving {file}")
            os.rename(os.path.join(doc_utils_path, file), os.path.join(generated_mkdocs_sourcefiles_path, file))
        elif file.endswith("png"):
            logger.debug(f"deleting {file}")
            os.remove(os.path.join(doc_utils_path, file))

    docs_tutorial_nbconvert_path = docs_tutorial_path.replace(".ipynb", ".nbconvert.ipynb")

    subprocess.run(
        ["jupyter", "nbconvert", "--to", "markdown", docs_tutorial_nbconvert_path], check=True)

    return docs_tutorial_nbconvert_path


if __name__ == "__main__":
    # md_doc_tuto_path = efootprint_tutorial_to_md()
    md_doc_tuto_path = os.path.join(doc_utils_path, "docs_tutorial.nbconvert.md")
    format_tutorial_and_save_to_mkdocs_sourcefiles(md_doc_tuto_path)
