import logging
from dotenv import load_dotenv
load_dotenv()

from pipeline.output import finalize_and_push

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    finalize_and_push()
