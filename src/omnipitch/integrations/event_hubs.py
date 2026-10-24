"""Optional Azure Event Hubs publisher for the live match event stream.

When AZURE_EVENT_HUB_CONNECTION_STRING is set (and the `azure-eventhub` package is
installed), every synthetic event is also published to the configured hub, so
downstream consumers — Azure Functions, Fabric Eventstream, Stream Analytics —
receive the same ingest feed the agents read. Without configuration this is a no-op.
"""

import json
import logging
import os
from typing import Optional

from omnipitch.models import MatchEvent

logger = logging.getLogger("omnipitch.event_hubs")


class EventHubPublisher:
    def __init__(self, connection_string: Optional[str] = None, hub_name: Optional[str] = None):
        self.connection_string = connection_string or os.getenv("AZURE_EVENT_HUB_CONNECTION_STRING", "")
        self.hub_name = hub_name or os.getenv("AZURE_EVENT_HUB_NAME", "match-events")
        self._producer = None
        self.published = 0
        self.failed = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.connection_string) and "..." not in self.connection_string

    async def _get_producer(self):
        if self._producer is None:
            from azure.eventhub.aio import EventHubProducerClient

            self._producer = EventHubProducerClient.from_connection_string(
                self.connection_string, eventhub_name=self.hub_name
            )
        return self._producer

    async def publish(self, event: MatchEvent) -> bool:
        """Publishes one event, partitioned by match so ordering is preserved per match."""
        if not self.is_configured:
            return False
        try:
            from azure.eventhub import EventData

            producer = await self._get_producer()
            batch = await producer.create_batch(partition_key=event.match_id)
            batch.add(EventData(json.dumps(event.model_dump())))
            await producer.send_batch(batch)
            self.published += 1
            return True
        except Exception as exc:  # never let ingest side-effects interrupt the broadcast
            self.failed += 1
            logger.warning("Event Hubs publish failed: %s", exc)
            return False

    def status(self) -> dict:
        return {
            "configured": self.is_configured,
            "hub": self.hub_name if self.is_configured else None,
            "published": self.published,
            "failed": self.failed,
        }


publisher = EventHubPublisher()
