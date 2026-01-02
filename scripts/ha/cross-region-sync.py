#!/usr/bin/env python3
"""
Cross-Region Data Synchronization
Synchronizes data across multiple regions for disaster recovery
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CrossRegionSync:
    """Manages data synchronization across regions"""
    
    def __init__(self):
        self.primary_region = os.getenv("PRIMARY_REGION", "us-east-1")
        self.secondary_regions = os.getenv("SECONDARY_REGIONS", "us-west-2,eu-west-1").split(",")
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", "300"))  # 5 minutes
        self.primary_db_url = os.getenv("PRIMARY_DATABASE_URL")
        self.secondary_db_urls = {
            region: os.getenv(f"{region.upper().replace('-', '_')}_DATABASE_URL")
            for region in self.secondary_regions
        }
        self.last_sync_timestamp = {}
    
    async def sync_memory_data(self, region: str, db_url: str):
        """Synchronize memory data to secondary region"""
        logger.info(f"Syncing memory data to {region}")
        
        try:
            # Connect to primary
            primary_conn = psycopg2.connect(self.primary_db_url)
            primary_cur = primary_conn.cursor(cursor_factory=RealDictCursor)
            
            # Get last sync timestamp
            last_sync = self.last_sync_timestamp.get(region, datetime.min)
            
            # Fetch new/updated memory entries
            primary_cur.execute("""
                SELECT id, tier, type, content, created_at, updated_at
                FROM memory_entries
                WHERE updated_at > %s OR created_at > %s
                ORDER BY updated_at ASC
            """, (last_sync, last_sync))
            
            memory_entries = primary_cur.fetchall()
            
            if not memory_entries:
                logger.debug(f"No new memory entries to sync to {region}")
                return
            
            # Connect to secondary
            secondary_conn = psycopg2.connect(db_url)
            secondary_cur = secondary_conn.cursor()
            
            # Sync entries
            synced_count = 0
            for entry in memory_entries:
                try:
                    secondary_cur.execute("""
                        INSERT INTO memory_entries (id, tier, type, content, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            tier = EXCLUDED.tier,
                            type = EXCLUDED.type,
                            content = EXCLUDED.content,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        entry["id"],
                        entry["tier"],
                        entry["type"],
                        entry["content"],
                        entry["created_at"],
                        entry["updated_at"]
                    ))
                    synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing memory entry {entry['id']}: {e}")
            
            secondary_conn.commit()
            self.last_sync_timestamp[region] = datetime.utcnow()
            
            logger.info(f"Synced {synced_count} memory entries to {region}")
            
            primary_cur.close()
            primary_conn.close()
            secondary_cur.close()
            secondary_conn.close()
            
        except Exception as e:
            logger.error(f"Error syncing memory data to {region}: {e}")
    
    async def sync_user_data(self, region: str, db_url: str):
        """Synchronize user data and preferences"""
        logger.info(f"Syncing user data to {region}")
        
        try:
            # Connect to primary
            primary_conn = psycopg2.connect(self.primary_db_url)
            primary_cur = primary_conn.cursor(cursor_factory=RealDictCursor)
            
            # Get last sync timestamp
            last_sync = self.last_sync_timestamp.get(f"{region}_userdata", datetime.min)
            
            # Fetch user preferences
            primary_cur.execute("""
                SELECT user_id, preferences, created_at, updated_at
                FROM user_preferences
                WHERE updated_at > %s
                ORDER BY updated_at ASC
            """, (last_sync,))
            
            user_prefs = primary_cur.fetchall()
            
            # Connect to secondary
            secondary_conn = psycopg2.connect(db_url)
            secondary_cur = secondary_conn.cursor()
            
            # Sync user preferences
            for pref in user_prefs:
                try:
                    secondary_cur.execute("""
                        INSERT INTO user_preferences (user_id, preferences, created_at, updated_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            preferences = EXCLUDED.preferences,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        pref["user_id"],
                        pref["preferences"],
                        pref["created_at"],
                        pref["updated_at"]
                    ))
                except Exception as e:
                    logger.error(f"Error syncing user preference {pref['user_id']}: {e}")
            
            secondary_conn.commit()
            self.last_sync_timestamp[f"{region}_userdata"] = datetime.utcnow()
            
            logger.info(f"Synced {len(user_prefs)} user preferences to {region}")
            
            primary_cur.close()
            primary_conn.close()
            secondary_cur.close()
            secondary_conn.close()
            
        except Exception as e:
            logger.error(f"Error syncing user data to {region}: {e}")
    
    async def sync_workflow_history(self, region: str, db_url: str):
        """Synchronize workflow execution history"""
        logger.info(f"Syncing workflow history to {region}")
        
        try:
            # Connect to primary
            primary_conn = psycopg2.connect(self.primary_db_url)
            primary_cur = primary_conn.cursor(cursor_factory=RealDictCursor)
            
            # Get last sync timestamp
            last_sync = self.last_sync_timestamp.get(f"{region}_workflows", datetime.min)
            
            # Fetch workflow history
            primary_cur.execute("""
                SELECT id, workflow_name, status, duration_seconds, tasks_completed,
                       created_at, parameters, summary
                FROM workflow_history
                WHERE created_at > %s
                ORDER BY created_at ASC
            """, (last_sync,))
            
            workflows = primary_cur.fetchall()
            
            # Connect to secondary
            secondary_conn = psycopg2.connect(db_url)
            secondary_cur = secondary_conn.cursor()
            
            # Sync workflows
            for workflow in workflows:
                try:
                    secondary_cur.execute("""
                        INSERT INTO workflow_history 
                        (id, workflow_name, status, duration_seconds, tasks_completed,
                         created_at, parameters, summary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                    """, (
                        workflow["id"],
                        workflow["workflow_name"],
                        workflow["status"],
                        workflow["duration_seconds"],
                        workflow["tasks_completed"],
                        workflow["created_at"],
                        workflow["parameters"],
                        workflow["summary"]
                    ))
                except Exception as e:
                    logger.error(f"Error syncing workflow {workflow['id']}: {e}")
            
            secondary_conn.commit()
            self.last_sync_timestamp[f"{region}_workflows"] = datetime.utcnow()
            
            logger.info(f"Synced {len(workflows)} workflow history entries to {region}")
            
            primary_cur.close()
            primary_conn.close()
            secondary_cur.close()
            secondary_conn.close()
            
        except Exception as e:
            logger.error(f"Error syncing workflow history to {region}: {e}")
    
    async def sync_to_region(self, region: str, db_url: str):
        """Synchronize all data to a secondary region"""
        logger.info(f"Starting full sync to {region}")
        
        await self.sync_memory_data(region, db_url)
        await self.sync_user_data(region, db_url)
        await self.sync_workflow_history(region, db_url)
        
        logger.info(f"Completed sync to {region}")
    
    async def sync_all_regions(self):
        """Synchronize data to all secondary regions"""
        tasks = []
        for region, db_url in self.secondary_db_urls.items():
            if db_url:
                tasks.append(self.sync_to_region(region, db_url))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_continuous_sync(self):
        """Run continuous synchronization"""
        logger.info("Starting continuous cross-region synchronization")
        
        while True:
            try:
                await self.sync_all_regions()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(self.sync_interval)


async def main():
    """Main entry point"""
    sync = CrossRegionSync()
    await sync.run_continuous_sync()


if __name__ == "__main__":
    asyncio.run(main())

