import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("PaperTrail")
# Set up logging for SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)