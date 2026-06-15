import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    from .kafka.consumer import HeraldConsumer
    logger.info("Starting HERALD Layer 5 content generation engine")
    consumer = HeraldConsumer(demo_mode=False)
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())
