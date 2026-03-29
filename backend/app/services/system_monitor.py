"""
System monitoring service - CPU, RAM, disk, network statistics.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

import psutil


@dataclass
class CpuStats:
    percent: float
    count: int
    per_cpu: List[float]
    load_avg: tuple


@dataclass
class MemoryStats:
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


@dataclass
class DiskStats:
    mount: str
    device: str
    total: int
    used: int
    free: int
    percent: float


@dataclass
class NetworkStats:
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int


@dataclass
class ProcessInfo:
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str


@dataclass
class SystemStats:
    timestamp: str
    uptime: int
    cpu: CpuStats
    memory: MemoryStats
    disks: List[DiskStats]
    network: NetworkStats
    top_processes: List[ProcessInfo] = field(default_factory=list)


def get_uptime() -> int:
    """Get system uptime in seconds."""
    return int(time.time() - psutil.boot_time())


def get_cpu_stats() -> CpuStats:
    """Get CPU statistics."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
    load_avg = os.getloadavg()
    
    return CpuStats(
        percent=cpu_percent,
        count=psutil.cpu_count(),
        per_cpu=per_cpu,
        load_avg=load_avg,
    )


def get_memory_stats() -> MemoryStats:
    """Get memory statistics."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return MemoryStats(
        total=mem.total,
        available=mem.available,
        used=mem.used,
        percent=mem.percent,
        swap_total=swap.total,
        swap_used=swap.used,
        swap_percent=swap.percent,
    )


def get_disk_stats() -> List[DiskStats]:
    """Get disk usage for all mounted partitions."""
    disks = []
    
    for partition in psutil.disk_partitions():
        # Skip special filesystems
        if partition.fstype in ("squashfs", "tmpfs", "devtmpfs"):
            continue
        if partition.mountpoint.startswith(("/snap", "/boot/efi")):
            continue
            
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append(DiskStats(
                mount=partition.mountpoint,
                device=partition.device,
                total=usage.total,
                used=usage.used,
                free=usage.free,
                percent=usage.percent,
            ))
        except PermissionError:
            continue
    
    return disks


def get_network_stats() -> NetworkStats:
    """Get network I/O statistics."""
    net = psutil.net_io_counters()
    
    return NetworkStats(
        bytes_sent=net.bytes_sent,
        bytes_recv=net.bytes_recv,
        packets_sent=net.packets_sent,
        packets_recv=net.packets_recv,
    )


def get_top_processes(limit: int = 10) -> List[ProcessInfo]:
    """Get top processes by CPU usage."""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = proc.info
            processes.append(ProcessInfo(
                pid=info['pid'],
                name=info['name'] or "unknown",
                username=info['username'] or "unknown",
                cpu_percent=info['cpu_percent'] or 0.0,
                memory_percent=info['memory_percent'] or 0.0,
                status=info['status'] or "unknown",
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Sort by CPU, then memory
    processes.sort(key=lambda p: (p.cpu_percent, p.memory_percent), reverse=True)
    return processes[:limit]


def get_system_stats(include_processes: bool = True) -> SystemStats:
    """Get all system statistics."""
    return SystemStats(
        timestamp=datetime.utcnow().isoformat(),
        uptime=get_uptime(),
        cpu=get_cpu_stats(),
        memory=get_memory_stats(),
        disks=get_disk_stats(),
        network=get_network_stats(),
        top_processes=get_top_processes() if include_processes else [],
    )


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"


def format_uptime(seconds: int) -> str:
    """Format uptime to human-readable string."""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) or "< 1m"
