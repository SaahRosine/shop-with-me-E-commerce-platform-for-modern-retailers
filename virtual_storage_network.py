import time
import hashlib
from typing import Dict, Optional, Tuple, List
from collections import defaultdict

from virtualstoragenode import StorageVirtualNode, FileTransfer, TransferStatus


class IPPool:
    """Simple IPv4 pool allocator within a subnet (e.g., 10.10.0.0/24)."""
    def __init__(self, base: str = "10.10.0.", start: int = 10, end: int = 250):
        self.base = base
        self.start = start
        self.end = end
        self.next = start
        self.assigned: Dict[str, str] = {}  # node_id -> ip

    def assign(self, node_id: str) -> Optional[str]:
        if node_id in self.assigned:
            return self.assigned[node_id]
        if self.next > self.end:
            return None
        ip = f"{self.base}{self.next}"
        self.assigned[node_id] = ip
        self.next += 1
        return ip

    def release(self, node_id: str):
        self.assigned.pop(node_id, None)


class StorageVirtualNetwork:
    def __init__(self, name: str = "ecom-network"):
        self.name = name
        self.nodes: Dict[str, StorageVirtualNode] = {}
        # Track transfers keyed by (source_id) -> file_id -> transfer (at target)
        self.transfer_operations: Dict[str, Dict[str, FileTransfer]] = defaultdict(dict)
        self.ip_pool = IPPool()

    def add_node(self, node: StorageVirtualNode) -> bool:
        """Add node and assign an IP."""
        if node.node_id in self.nodes:
            return False
        ip = self.ip_pool.assign(node.node_id)
        if not ip:
            return False
        node.set_ip(ip)
        self.nodes[node.node_id] = node
        return True

    def connect_nodes(self, node1_id: str, node2_id: str, bandwidth_mbps: int) -> bool:
        """Bidirectional connection with specified link bandwidth."""
        n1 = self.nodes.get(node1_id)
        n2 = self.nodes.get(node2_id)
        if not n1 or not n2:
            return False
        n1.add_connection(node2_id, bandwidth_mbps)
        n2.add_connection(node1_id, bandwidth_mbps)
        return True

    def _generate_file_id(self, file_name: str) -> str:
        return hashlib.md5(f"{file_name}-{time.time()}".encode()).hexdigest()

    def initiate_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_name: str,
        file_size_bytes: int
    ) -> Optional[FileTransfer]:
        """Create a transfer record on target, reserved storage and chunk plan."""
        src = self.nodes.get(source_node_id)
        tgt = self.nodes.get(target_node_id)
        if not src or not tgt:
            return None

        file_id = self._generate_file_id(file_name)
        transfer = tgt.initiate_incoming_transfer(file_id, file_name, file_size_bytes, source_node_id)
        if transfer:
            transfer.status = TransferStatus.IN_PROGRESS
            self.transfer_operations[source_node_id][file_id] = transfer
            return transfer
        return None

    def process_file_transfer(
        self,
        source_node_id: str,
        target_node_id: str,
        file_id: str,
        chunks_per_step: int = 1
    ) -> Tuple[int, bool]:
        """Advance transfer by N chunks; returns (chunks_done, is_completed)."""
        src = self.nodes.get(source_node_id)
        tgt = self.nodes.get(target_node_id)
        if not src or not tgt:
            return (0, False)

        transfer_map = self.transfer_operations.get(source_node_id, {})
        transfer = transfer_map.get(file_id)
        if not transfer:
            return (0, False)

        chunks_transferred = 0
        for chunk in transfer.chunks:
            if chunk.status == TransferStatus.COMPLETED:
                continue
            if chunks_transferred >= chunks_per_step:
                break

            ok = tgt.process_chunk_transfer(file_id, chunk.chunk_id, source_node_id)
            if ok:
                chunks_transferred += 1
            else:
                # congestion or no link; pause this step
                break

        if transfer.status == TransferStatus.COMPLETED:
            # Transfer finished; remove tracking
            del self.transfer_operations[source_node_id][file_id]
            return (chunks_transferred, True)

        return (chunks_transferred, False)

    def get_network_stats(self) -> Dict[str, float]:
        total_bandwidth_bps = sum(n.bandwidth_bps for n in self.nodes.values())
        used_bandwidth_bps = sum(n.network_utilization_bps for n in self.nodes.values())
        total_storage_bytes = sum(n.total_storage for n in self.nodes.values())
        used_storage_bytes = sum(n.used_storage for n in self.nodes.values())
        active_transfers = sum(len(t) for t in self.transfer_operations.values())

        return {
            "total_nodes": float(len(self.nodes)),
            "total_bandwidth_bps": float(total_bandwidth_bps),
            "used_bandwidth_bps": float(used_bandwidth_bps),
            "bandwidth_utilization_percent": (used_bandwidth_bps / total_bandwidth_bps * 100) if total_bandwidth_bps > 0 else 0.0,
            "total_storage_bytes": float(total_storage_bytes),
            "used_storage_bytes": float(used_storage_bytes),
            "storage_utilization_percent": (used_storage_bytes / total_storage_bytes * 100) if total_storage_bytes > 0 else 0.0,
            "active_transfers": float(active_transfers),
        }

    def list_nodes(self) -> List[Dict[str, str]]:
        return [
            {
                "node_id": n.node_id,
                "role": n.role,
                "ip": n.ip_address or "unassigned"
            } for n in self.nodes.values()
        ]
