import asyncio
import logging

from app.core.config import get_settings
from app.worker.event_worker import process_event_batch
from app.worker.recluster_worker import process_next_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    logger.info("Worker started")
    while True:
        try:
            processed_events = await process_event_batch(
                settings.worker_batch_size
            )
            processed_runs = await process_next_run()
            if processed_events or processed_runs:
                logger.info(
                    "Processed events=%s runs=%s",
                    processed_events,
                    processed_runs,
                )
        except Exception:
            logger.exception("Worker iteration failed")
        await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run())

