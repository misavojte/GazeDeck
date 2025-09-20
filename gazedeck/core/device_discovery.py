# gazedeck/core/device_discovery.py
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Dict, List, Optional

from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
from pupil_labs.realtime_api.device import Device

# Set up logging for debugging
logger = logging.getLogger(__name__)

SERVICE_TYPE = "_http._tcp.local."
PL_NAME_PREFIX = "PI monitor:"  # PI monitor:<phone name>:<phone hw id>._http._tcp.local.


def enable_discovery_debug_logging():
    """
    Enable detailed debug logging for device discovery.
    Call this before running discovery to see detailed information about the process.
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.setLevel(logging.DEBUG)
    # Also enable zeroconf logging
    zeroconf_logger = logging.getLogger('zeroconf')
    zeroconf_logger.setLevel(logging.INFO)

async def _race_connect(all_addrs: List[str], port: int, timeout: float = 2.0) -> Optional[Device]:
    """
    Try all advertised IPs (IPv4 and IPv6) for one service instance in parallel.
    Return the first `Device` whose TCP connect succeeds; otherwise None.

    Rationale:
    - Devices often advertise multiple A/AAAA records (multihomed phones, stale
      addresses). Picking the “first” address is brittle on multi-NIC hosts.
    - Racing eliminates subnet guesswork and first-address bias.
    """
    async def try_ip(ip: str):
        try:
            logger.debug(f"Attempting connection to {ip}:{port}")
            # Works for IPv4 and IPv6 literals.
            r, w = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout)
            w.close()
            with suppress(Exception):
                await w.wait_closed()
            logger.debug(f"Successfully connected to {ip}:{port}")
            return Device(address=ip, port=port)
        except Exception as e:
            logger.debug(f"Failed to connect to {ip}:{port}: {e}")
            return None

    tasks = [asyncio.create_task(try_ip(ip)) for ip in all_addrs]
    if not tasks:
        return None
    try:
        for t in asyncio.as_completed(tasks):
            dev = await t
            if dev:
                for tt in tasks:
                    if tt is not t:
                        tt.cancel()
                return dev
        return None
    finally:
        for tt in tasks:
            with suppress(Exception):
                tt.cancel()

async def discover_devices_indexed(duration: float = 3.0) -> Dict[int, Device]:
    """
    Discover Pupil Labs realtime endpoints via mDNS and return {index: Device}.

    How it differs from the SDK helper:
    - We do *not* use `pupil_labs.realtime_api.discovery.discover_devices`
      because in multi-NIC setups it can miss devices. Instead, we:
        1) Browse `_http._tcp.local.` across all local interfaces.
        2) Keep only services whose name starts with `PI monitor:`.
        3) For each service, *race* all advertised IPv4+IPv6 addresses on the
           advertised port and build `Device` from the winner.

    Discovery behavior:
    - Waits for the full `duration` seconds to discover all available devices
    - After the discovery period, waits 0.5 additional seconds to finish
      connecting to any devices that were in the process of being discovered.

    Deterministic output:
    - We dedupe by service instance name and return a stable index ordered by name.

    Note:
    - mDNS must be delivered on the local link. If multicast is blocked, no
      mDNS-based approach will discover the device; use direct IP in such cases.
    """
    logger.info(f"Starting device discovery for {duration} seconds...")
    azc = AsyncZeroconf()  # binds across all local NICs (IPv4/IPv6)
    by_name: Dict[str, Device] = {}
    services_seen = 0

    def on_service_state_change(zeroconf, service_type: str, name: str, state_change: ServiceStateChange) -> None:
        """Synchronous handler that creates async task for processing"""
        nonlocal services_seen
        services_seen += 1
        logger.debug(f"Service state change: {name} -> {state_change}")
        asyncio.create_task(process_service_change(zeroconf, service_type, name, state_change))

    async def process_service_change(zeroconf, service_type: str, name: str, state_change: ServiceStateChange):
        """Process service state changes asynchronously"""
        try:
            if state_change != ServiceStateChange.Added:
                logger.debug(f"Ignoring non-added state for {name}: {state_change}")
                return
            
            logger.debug(f"Processing service: {name}")
            if not name.startswith(PL_NAME_PREFIX):
                logger.debug(f"Ignoring service (wrong prefix): {name}")
                return
            
            logger.info(f"Found Pupil Labs device service: {name}")
            
            info = await azc.async_get_service_info(service_type, name, timeout=3000)  # 3 second timeout
            if not info:
                logger.warning(f"Could not get service info for {name}")
                return

            logger.debug(f"Service info for {name}: port={info.port}, addresses={info.addresses}")

            # Include BOTH IPv4 and IPv6 addresses
            addrs: List[str] = info.parsed_scoped_addresses() or []
            if not addrs:
                logger.warning(f"No addresses found for {name}")
                return

            logger.info(f"Attempting connection to {name} at addresses: {addrs}, port: {info.port}")
            dev = await _race_connect(addrs, info.port)
            if dev:
                logger.info(f"Successfully connected to device: {name} -> {dev.address}:{dev.port}")
                by_name.setdefault(name, dev)
            else:
                logger.warning(f"Failed to connect to any address for {name}")
        except Exception as e:
            logger.error(f"Error processing service {name}: {e}")

    browser = AsyncServiceBrowser(
        azc.zeroconf,
        SERVICE_TYPE,
        handlers=[on_service_state_change],
    )

    try:
        logger.info(f"Browsing for services of type: {SERVICE_TYPE}")
        # Wait for the full discovery duration
        await asyncio.sleep(duration)

    finally:
        logger.debug("Cleaning up discovery resources...")
        await browser.async_cancel()
        await azc.async_close()

    logger.info(f"Discovery complete. Services seen: {services_seen}, Devices connected: {len(by_name)}")
    if by_name:
        logger.info("Found devices:")
        for name, dev in by_name.items():
            logger.info(f"  {name} -> {dev.address}:{dev.port}")
    else:
        logger.warning("No devices found during discovery")

    items = sorted(by_name.items(), key=lambda kv: kv[0])
    return {i: dev for i, (_, dev) in enumerate(items)}