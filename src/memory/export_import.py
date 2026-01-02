"""
Memory Export/Import Functionality
"""

import json
import logging
import gzip
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryExporter:
    """Export memory data"""
    
    def __init__(self, postgres_backend):
        """Initialize exporter"""
        self.postgres = postgres_backend
        self.logger = logging.getLogger("memory.exporter")
    
    def export(
        self,
        output_path: str,
        tier: Optional[str] = None,
        agent: Optional[str] = None,
        project: Optional[str] = None,
        include_deleted: bool = False,
        compress: bool = True
    ) -> bool:
        """
        Export memory entries to file.
        
        Args:
            output_path: Output file path
            tier: Filter by tier
            agent: Filter by agent
            project: Filter by project
            include_deleted: Include soft-deleted entries
            compress: Compress output file
        
        Returns:
            True if successful
        """
        try:
            # Get entries
            entries = self.postgres.retrieve(
                tier=tier,
                agent=agent,
                project=project,
                include_deleted=include_deleted,
                limit=1000000  # Large limit
            )
            
            # Prepare export data
            export_data = {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "filters": {
                    "tier": tier,
                    "agent": agent,
                    "project": project,
                    "include_deleted": include_deleted
                },
                "total_entries": len(entries),
                "entries": entries
            }
            
            # Write to file
            output_file = Path(output_path)
            if compress:
                output_file = output_file.with_suffix(output_file.suffix + ".gz")
                with gzip.open(output_file, "wt", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, default=str)
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Exported {len(entries)} entries to {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False


class MemoryImporter:
    """Import memory data"""
    
    def __init__(self, postgres_backend):
        """Initialize importer"""
        self.postgres = postgres_backend
        self.logger = logging.getLogger("memory.importer")
    
    def import_file(
        self,
        input_path: str,
        merge_strategy: str = "skip",  # "skip", "overwrite", "merge"
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Import memory entries from file.
        
        Args:
            input_path: Input file path
            merge_strategy: How to handle existing entries
            validate: Validate entries before importing
        
        Returns:
            Import statistics
        """
        stats = {
            "total": 0,
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "errors_list": []
        }
        
        try:
            # Read file
            input_file = Path(input_path)
            if input_file.suffix == ".gz":
                with gzip.open(input_file, "rt", encoding="utf-8") as f:
                    import_data = json.load(f)
            else:
                with open(input_file, "r", encoding="utf-8") as f:
                    import_data = json.load(f)
            
            entries = import_data.get("entries", [])
            stats["total"] = len(entries)
            
            # Import entries
            for entry in entries:
                try:
                    # Validate if requested
                    if validate and not self._validate_entry(entry):
                        stats["skipped"] += 1
                        continue
                    
                    # Check if exists
                    existing = self.postgres.retrieve(entry_id=entry["id"], limit=1)
                    
                    if existing:
                        if merge_strategy == "skip":
                            stats["skipped"] += 1
                            continue
                        elif merge_strategy == "overwrite":
                            self.postgres.update(entry["id"], entry)
                            stats["imported"] += 1
                        elif merge_strategy == "merge":
                            # Merge metadata
                            merged = {**existing[0], **entry}
                            self.postgres.update(entry["id"], merged)
                            stats["imported"] += 1
                    else:
                        # New entry
                        self.postgres.store(entry)
                        stats["imported"] += 1
                
                except Exception as e:
                    stats["errors"] += 1
                    stats["errors_list"].append({
                        "entry_id": entry.get("id", "unknown"),
                        "error": str(e)
                    })
                    self.logger.error(f"Failed to import entry: {e}")
            
            self.logger.info(
                f"Imported {stats['imported']}/{stats['total']} entries "
                f"(skipped: {stats['skipped']}, errors: {stats['errors']})"
            )
            
            return stats
        
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            stats["errors"] += 1
            stats["errors_list"].append({"error": str(e)})
            return stats
    
    def _validate_entry(self, entry: Dict[str, Any]) -> bool:
        """Validate entry structure"""
        required_fields = ["id", "tier", "type", "content"]
        return all(field in entry for field in required_fields)

