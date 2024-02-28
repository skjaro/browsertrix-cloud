"""
Migration 0026 -- Crawl Pages
"""

from btrixcloud.migrations import BaseMigration


MIGRATION_VERSION = "0026"


class Migration(BaseMigration):
    """Migration class."""

    def __init__(self, mdb, **kwargs):
        super().__init__(mdb, migration_version=MIGRATION_VERSION)
        self.page_ops = kwargs["page_ops"]

    async def migrate_up(self):
        """Perform migration up.

        Add pages to database for each crawl without them, pulling from WACZ files.
        """
        # pylint: disable=duplicate-code
        crawls_mdb = self.mdb["crawls"]
        pages_mdb = self.mdb["pages"]

        print("Getting crawl ids", flush=True)
        crawl_ids = await crawls_mdb.distinct(
            "_id", {"type": "crawl", "finished": {"$ne": None}}
        )
        print(f"Crawl ids: {crawl_ids}", flush=True)

        print("Getting crawl ids with pages")
        crawl_ids_with_pages = await pages_mdb.distinct("crawl_id")
        print(f"Crawl ids with pages: {crawl_ids_with_pages}", flush=True)

        print("Calculating crawl ids with no pages", flush=True)
        crawl_ids_no_pages = list(set(crawl_ids) - set(crawl_ids_with_pages))
        print(f"Crawl ids with no pages: {crawl_ids_no_pages}", flush=True)
        if not crawl_ids_no_pages:
            return

        for crawl_id in crawl_ids_no_pages:
            try:
                print(f"Adding crawl pages to db for crawl {crawl_id}", flush=True)
                await self.page_ops.add_crawl_pages_to_db_from_wacz(crawl_id)
                print(
                    f"Finished adding crawl pages to db for crawl {crawl_id}",
                    flush=True,
                )
            # pylint: disable=broad-exception-caught, raise-missing-from
            except Exception as err:
                print(
                    f"Error adding pages to db for crawl {crawl_id}: {err}", flush=True
                )
