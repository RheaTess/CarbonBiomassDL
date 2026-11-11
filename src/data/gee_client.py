
import os
import ee

from pathlib import Path
from dotenv import load_dotenv


# Locate .env in the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


def initialize_earth_engine():

    load_dotenv(dotenv_path=ENV_FILE)

    project_id = os.getenv("EARTH_ENGINE_PROJECT_ID")

    if not project_id:
        raise ValueError(
            f"EARTH_ENGINE_PROJECT_ID is missing. "
            f"Check your .env file at: {ENV_FILE}"
        )

    try:
        ee.Initialize(project=project_id)

    except Exception as error:
        raise RuntimeError(
            f"Earth Engine initialization failed: {error}"
        )

    return True
