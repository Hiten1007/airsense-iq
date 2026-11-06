import os
import shutil
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def build_github_pages_site():
    """
    Build static website artifacts into the 'docs/' directory for GitHub Pages hosting.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_src = os.path.join(project_root, "templates", "index.html")
    docs_dir = os.path.join(project_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    dest_html = os.path.join(docs_dir, "index.html")
    shutil.copyfile(template_src, dest_html)
    logger.info(f"Copied dashboard template to {dest_html}")

    # Copy latest predictions json if available
    predictions_src = os.path.join(project_root, "data", "latest_predictions.json")
    if os.path.exists(predictions_src):
        dest_data = os.path.join(docs_dir, "latest_predictions.json")
        shutil.copyfile(predictions_src, dest_data)
        logger.info(f"Exported prediction data payload to {dest_data}")

    # Create .nojekyll so GitHub Pages doesn't ignore files
    nojekyll_path = os.path.join(docs_dir, ".nojekyll")
    with open(nojekyll_path, "w") as f:
        f.write("")

    logger.info("GitHub Pages static site generated in docs/")


if __name__ == "__main__":
    build_github_pages_site()
