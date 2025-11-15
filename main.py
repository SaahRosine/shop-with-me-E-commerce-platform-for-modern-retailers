import time
import math
import sys
from typing import Tuple

from virtual_storage_network import StorageVirtualNetwork
from virtualstoragenode import StorageVirtualNode


def progress_bar(label: str, progress: float, width: int = 40):
    filled = int(progress * width)
    bar = "[" + "#" * filled + "-" * (width - filled) + "]"
    sys.stdout.write(f"\r{label} {bar} {int(progress*100)}%")
    sys.stdout.flush()


def pretty_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.2f} {units[i]}"


def create_ecommerce_topology() -> StorageVirtualNetwork:
    """Builds a small e-commerce cloud: web, app, db, cache nodes."""
    net = StorageVirtualNetwork(name="small-retail-ecom")

    web = StorageVirtualNode("web-1", role="web", cpu_capacity=4, memory_capacity=8, storage_capacity=50, bandwidth_mbps=500)
    app = StorageVirtualNode("app-1", role="app", cpu_capacity=6, memory_capacity=16, storage_capacity=100, bandwidth_mbps=800)
    db = StorageVirtualNode("db-1", role="db", cpu_capacity=8, memory_capacity=32, storage_capacity=500, bandwidth_mbps=1000)
    cache = StorageVirtualNode("cache-1", role="cache", cpu_capacity=2, memory_capacity=4, storage_capacity=20, bandwidth_mbps=300)

    for node in (web, app, db, cache):
        assert net.add_node(node), f"Failed to add {node.node_id}"

    # Connect typical flows
    assert net.connect_nodes("web-1", "app-1", bandwidth_mbps=300)
    assert net.connect_nodes("app-1", "db-1", bandwidth_mbps=500)
    assert net.connect_nodes("app-1", "cache-1", bandwidth_mbps=400)
    # Optional: web direct to cache for static assets
    assert net.connect_nodes("web-1", "cache-1", bandwidth_mbps=200)

    return net


def simulate_transfer(
    net: StorageVirtualNetwork,
    source_id: str,
    target_id: str,
    file_name: str,
    file_size_bytes: int,
    step_chunks: int = 3
) -> Tuple[bool, str]:
    transfer = net.initiate_file_transfer(source_id, target_id, file_name, file_size_bytes)
    if not transfer:
        print(f"\nFailed to initiate transfer {file_name} from {source_id} to {target_id}")
        return False, ""

    file_id = transfer.file_id
    total_chunks = len(transfer.chunks)
    completed = False
    transferred_chunks = 0

    print(f"\nInitiated transfer {file_name} ({pretty_bytes(file_size_bytes)}) from {source_id} to {target_id}")
    while not completed:
        done, completed = net.process_file_transfer(source_id, target_id, file_id, chunks_per_step=step_chunks)
        transferred_chunks += done
        progress = min(transferred_chunks / total_chunks, 1.0)
        progress_bar(f"Transferring {file_name}", progress)
        time.sleep(0.1)

    # Finish line
    progress_bar(f"Transferring {file_name}", 1.0)
    print("\nTransfer completed.")
    return True, file_id


def print_network_state(net: StorageVirtualNetwork):
    nodes = net.list_nodes()
    print("\nCloud topology (nodes and IPs):")
    for n in nodes:
        print(f" - {n['node_id']:8s} [{n['role']:5s}] IP: {n['ip']}")

    stats = net.get_network_stats()
    print("\nNetwork stats:")
    print(f" - Nodes: {int(stats['total_nodes'])}")
    print(f" - Bandwidth used: {pretty_bytes(stats['used_bandwidth_bps']/8)} / {pretty_bytes(stats['total_bandwidth_bps']/8)} "
          f"({stats['bandwidth_utilization_percent']:.2f}%)")
    print(f" - Storage used: {pretty_bytes(stats['used_storage_bytes'])} / {pretty_bytes(stats['total_storage_bytes'])} "
          f"({stats['storage_utilization_percent']:.2f}%)")
    print(f" - Active transfers: {int(stats['active_transfers'])}")


def main():
    net = create_ecommerce_topology()
    print_network_state(net)

    # Simulate common e-commerce flows:
    # 1) Web uploads product images to app (which stores to db through app->db transfer)
    #    For simplicity, we simulate direct web->db storage via app path represented as a single transfer.
    simulate_transfer(net, "web-1", "app-1", "product_image_01.jpg", 12 * 1024 * 1024, step_chunks=4)
    print_network_state(net)

    # 2) App writes large order export to DB
    simulate_transfer(net, "app-1", "db-1", "orders_export.csv", 180 * 1024 * 1024, step_chunks=5)
    print_network_state(net)

    # 3) DB replicates nightly backup to cache node (pretend cache as backup store here)
    simulate_transfer(net, "db-1", "cache-1", "nightly_backup.bin", 300 * 1024 * 1024, step_chunks=6)
    print_network_state(net)

    # 4) Concurrent transfers example: app pushes static bundle to web, while web pulls from cache
    print("\nStarting concurrent transfers...")
    # Kick off two transfers and interleave processing manually
    t1 = net.initiate_file_transfer("app-1", "web-1", "static_bundle.tar", 90 * 1024 * 1024)
    t2 = net.initiate_file_transfer("cache-1", "web-1", "hero_banner.webp", 25 * 1024 * 1024)

    if not (t1 and t2):
        print("Failed to start concurrent transfers.")
    else:
        chunks_web_total = len(t1.chunks) + len(t2.chunks)
        chunks_done = 0
        completed1 = False
        completed2 = False

        while not (completed1 and completed2):
            d1, completed1 = net.process_file_transfer("app-1", "web-1", t1.file_id, chunks_per_step=2) if not completed1 else (0, True)
            d2, completed2 = net.process_file_transfer("cache-1", "web-1", t2.file_id, chunks_per_step=2) if not completed2 else (0, True)
            chunks_done += (d1 + d2)
            progress = min(chunks_done / chunks_web_total, 1.0)
            progress_bar("Concurrent deliveries to web-1", progress)
            time.sleep(0.1)

        progress_bar("Concurrent deliveries to web-1", 1.0)
        print("\nConcurrent transfers completed.")
        print_network_state(net)

    print("\nSimulation finished.")


if __name__ == "__main__":
    main()
