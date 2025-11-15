import time
import math
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Union
from enum import Enum, auto


class TransferStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class FileChunk:
    chunk_id: int
    size: int  # bytes
    checksum: str
    status: TransferStatus = TransferStatus.PENDING
    stored_node: Optional[str] = None


@dataclass
class FileTransfer:
    file_id: str
    file_name: str
    total_size: int  # bytes
    chunks: List[FileChunk]
    status: TransferStatus = TransferStatus.PENDING
    created_at: float = time.time()
    completed_at: Optional[float] = None
    source_node_id: Optional[str] = None
    target_node_id: Optional[str] = None


class StorageVirtualNode:
    def __init__(
        self,
        node_id: str,
        role: str,
        cpu_capacity: int,       # vCPUs
        memory_capacity: int,    # GB
        storage_capacity: int,   # GB
        bandwidth_mbps: int,     # Mbps (node NIC)
        ip_address: Optional[str] = None,
    ):
        self.node_id = node_id
        self.role = role  # e.g., "web", "app", "db", "cache"
        self.cpu_capacity = cpu_capacity
        self.memory_capacity = memory_capacity
        self.total_storage = storage_capacity * 1024 * 1024 * 1024  # bytes
        self.bandwidth_bps = bandwidth_mbps * 1_000_000            # bits per second
        self.ip_address = ip_address

        # Utilization
        self.used_storage = 0  # bytes
        self.network_utilization_bps = 0.0  # instantaneous utilization (bps)

        # Transfer and file tracking
        self.active_transfers: Dict[str, FileTransfer] = {}
        self.stored_files: Dict[str, FileTransfer] = {}

        # Performance metrics
        self.total_requests_processed = 0
        self.total_data_transferred_bytes = 0
        self.failed_transfers = 0

        # Network connections (peer_node_id -> link_bandwidth_bps)
        self.connections: Dict[str, int] = {}

    def add_connection(self, peer_node_id: str, link_bandwidth_mbps: int):
        """Add a network connection to another node."""
        self.connections[peer_node_id] = link_bandwidth_mbps * 1_000_000

    def set_ip(self, ip_address: str):
        self.ip_address = ip_address

    def _calculate_chunk_size(self, file_size: int) -> int:
        """Heuristic chunk size based on file size."""
        if file_size < 10 * 1024 * 1024:      # < 10MB
            return 512 * 1024                 # 512KB
        elif file_size < 100 * 1024 * 1024:   # < 100MB
            return 2 * 1024 * 1024            # 2MB
        else:
            return 10 * 1024 * 1024           # 10MB

    def _generate_chunks(self, file_id: str, file_size: int) -> List[FileChunk]:
        chunk_size = self._calculate_chunk_size(file_size)
        num_chunks = math.ceil(file_size / chunk_size)
        chunks = []
        for i in range(num_chunks):
            fake_checksum = hashlib.md5(f"{file_id}-{i}".encode()).hexdigest()
            actual_chunk_size = min(chunk_size, file_size - i * chunk_size)
            chunks.append(FileChunk(
                chunk_id=i,
                size=actual_chunk_size,
                checksum=fake_checksum
            ))
        return chunks

    def initiate_incoming_transfer(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        source_node_id: str
    ) -> Optional[FileTransfer]:
        """Prepare to receive a file (storage reservation + chunk plan)."""
        if self.used_storage + file_size > self.total_storage:
            self.failed_transfers += 1
            return None

        chunks = self._generate_chunks(file_id, file_size)
        transfer = FileTransfer(
            file_id=file_id,
            file_name=file_name,
            total_size=file_size,
            chunks=chunks,
            status=TransferStatus.PENDING,
            source_node_id=source_node_id,
            target_node_id=self.node_id
        )
        self.active_transfers[file_id] = transfer
        return transfer

    def process_chunk_transfer(
        self,
        file_id: str,
        chunk_id: int,
        source_node_id: str
    ) -> bool:
        """Receive a chunk from source_node_id, consume link+NIC bandwidth, store it."""
        if file_id not in self.active_transfers:
            return False

        transfer = self.active_transfers[file_id]
        try:
            chunk = next(c for c in transfer.chunks if c.chunk_id == chunk_id)
        except StopIteration:
            return False

        # Link is capped by both NIC and connection
        link_bps = self.connections.get(source_node_id, 0)
        if link_bps <= 0:
            return False

        available_bps = min(
            max(self.bandwidth_bps - int(self.network_utilization_bps), 0),
            link_bps
        )
        if available_bps <= 0:
            # Congested; caller can retry later
            return False

        # Simulate transfer time
        chunk_bits = chunk.size * 8
        transfer_time = chunk_bits / available_bps
        time.sleep(min(transfer_time, 0.2))  # cap sleep for snappy simulation

        # Mark chunk
        chunk.status = TransferStatus.COMPLETED
        chunk.stored_node = self.node_id

        # Update metrics
        # Simulate bursty utilization peaking during transfer
        self.network_utilization_bps = min(self.bandwidth_bps, available_bps * 0.8)
        self.total_data_transferred_bytes += chunk.size

        # If all chunks done, finalize
        if all(c.status == TransferStatus.COMPLETED for c in transfer.chunks):
            transfer.status = TransferStatus.COMPLETED
            transfer.completed_at = time.time()
            self.used_storage += transfer.total_size
            self.stored_files[file_id] = transfer
            del self.active_transfers[file_id]
            self.total_requests_processed += 1

        return True

    def retrieve_file_manifest(self, file_id: str) -> Optional[FileTransfer]:
        """Return manifest for a stored file to initiate outbound transfer elsewhere."""
        return self.stored_files.get(file_id)

    def get_storage_utilization(self) -> Dict[str, Union[int, float]]:
        total = self.total_storage
        used = self.used_storage
        return {
            "used_bytes": used,
            "total_bytes": total,
            "utilization_percent": (used / total * 100) if total > 0 else 0.0,
            "files_stored": len(self.stored_files),
            "active_transfers": len(self.active_transfers),
        }

    def get_network_utilization(self) -> Dict[str, Union[int, float, List[str]]]:
        max_bps = self.bandwidth_bps
        return {
            "current_utilization_bps": self.network_utilization_bps,
            "max_bandwidth_bps": max_bps,
            "utilization_percent": (self.network_utilization_bps / max_bps * 100) if max_bps > 0 else 0.0,
            "connections": list(self.connections.keys()),
        }

    def get_performance_metrics(self) -> Dict[str, int]:
        return {
            "total_requests_processed": self.total_requests_processed,
            "total_data_transferred_bytes": self.total_data_transferred_bytes,
            "failed_transfers": self.failed_transfers,
            "current_active_transfers": len(self.active_transfers),
        }
