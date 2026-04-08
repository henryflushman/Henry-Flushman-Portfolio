# Ephemeris_Cache.py
""" For Solar_System_Sim.py

Background chunk computation to avoid blocking the GUI.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, Future

import numpy as np

# local orbit functions
import Orbits_Functions as of

# ---------------- CONFIG ---------------- #

PLANET_IDS = {
    "Mercury": 1,
    "Venus":   2,
    "Earth":   3,
    "Mars":    4,
    "Jupiter": 5,
    "Saturn":  6,
    "Uranus":  7,
    "Neptune": 8,
}

PLANET_NAMES = list(PLANET_IDS.keys())

J2000_DATETIME = datetime(2000, 1, 1, 12, 0, 0)  # J2000.0 day

AU_KM = 149_597_870.0
SECONDS_PER_DAY = 86400.0


@dataclass
class EphemerisChunk:
    """ Ephemeris data for a single time chunk """
    index: int
    times_days: np.ndarray      # (N,)
    positions: np.ndarray       # (n_planets, N, 3)
    velocities: np.ndarray      # (n_planets, N, 3)

    def positions_at(self, t_days: float) -> np.ndarray:
        """Interpolate positions at absolute time t_days (days since J2000)."""
        times = self.times_days

        # Chunk clamping
        t = float(np.clip(t_days, times[0], times[-1]))

        # Indexing for interpolation
        idx = int(np.searchsorted(times, t) - 1)
        idx = max(0, min(idx, len(times) - 2))

        t0, t1 = times[idx], times[idx + 1]
        h = t1 - t0
        if h <= 0:
            return self.positions[:, idx, :]

        # Normalize time to [0,1]
        tau = (t - t0) / h

        # Hermite interpolative method
        tau2 = tau * tau
        tau3 = tau2 * tau

        h00 = 2 * tau3 - 3 * tau2 + 1
        h10 = tau3 - 2 * tau2 + tau
        h01 = -2 * tau3 + 3 * tau2
        h11 = tau3 - tau2

        P0 = self.positions[:, idx, :]
        P1 = self.positions[:, idx + 1, :]
        V0 = self.velocities[:, idx, :]
        V1 = self.velocities[:, idx + 1, :]

        # Hermite interpolation calculations
        return (
            h00 * P0 +
            h10 * h * V0 +
            h01 * P1 +
            h11 * h * V1
        )


class EphemerisCache:
    """
    Chunked ephemeris cache with background computation:
    - Synchronously ensure a short initial fragment of chunk 0 is available so the sim can start.
    - The full chunk(s) are computed in a background worker.
    - If a requested chunk is not yet ready, return clamped positions
      from the nearest available cached chunk to avoid blocking the GUI.
    """

    def __init__(
        self,
        chunk_years: float = 25.0,
        step_days: float = 1.0,
        cache_dir: str | Path = "ephem_cache",
        max_chunk_in_memory: int = 3,
        max_years: Optional[float] = None,
        max_workers: int = 1,
        initial_sync_days: float = 10.0,   # <-- small synchronous span (days) for fast startup
    ) -> None:
        self.chunk_years = float(chunk_years)
        self.chunk_days = self.chunk_years * 365.25
        self.step_days = float(step_days)

        if self.step_days <= 0:
            raise ValueError("step_days must be > 0")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_chunk_in_memory = int(max_chunk_in_memory)

        self.max_years = float(max_years) if max_years is not None else None
        self.max_days = self.max_years * 365.25 if self.max_years else None

        # In-memory caches and synchronization
        self._cache: Dict[int, EphemerisChunk] = {}
        self._lock = threading.Lock()
        self._computing: set[int] = set()
        self._futures: Dict[int, Future] = {}

        # Background executor for chunk computation
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # Try to load chunk 0 from disk if present (non-blocking load path)
        self._ensure_chunk_ready(0, sync=False)

        # If chunk 0 still not present, compute a very small initial fragment synchronously
        with self._lock:
            if 0 not in self._cache:
                # limit initial_sync to not exceed the chunk length or overall max_days
                init_days = float(min(initial_sync_days, self.chunk_days))
                if self.max_days is not None:
                    init_days = min(init_days, self.max_days)

                start_days = 0.0
                end_days = start_days + init_days

                times_days = np.arange(start_days, end_days + 1e-6, self.step_days, dtype=float)
                n_steps = len(times_days)
                planet_ids = list(PLANET_IDS.values())
                n_planets = len(planet_ids)

                positions = np.zeros((n_planets, n_steps, 3), dtype=np.float32)
                velocities = np.zeros_like(positions)

                # Compute small synchronous fragment (fast enough for UI startup)
                for j, t_days in enumerate(times_days):
                    current_dt = J2000_DATETIME + timedelta(days=float(t_days))
                    y, m, d = current_dt.year, current_dt.month, current_dt.day
                    H, Min, S = current_dt.hour, current_dt.minute, current_dt.second

                    for i, pid in enumerate(planet_ids):
                        r_vec, v_vec = of.date_to_planet_rv(pid, y, m, d, H, Min, S)
                        r = np.asarray(r_vec, dtype=np.float32)
                        v = np.asarray(v_vec, dtype=np.float32)
                        positions[i, j, :] = r / AU_KM
                        velocities[i, j, :] = v * (SECONDS_PER_DAY / AU_KM)

                chunk = EphemerisChunk(index=0, times_days=times_days, positions=positions, velocities=velocities)
                self._cache[0] = chunk

                # Schedule full chunk 0 compute in the background (if not already computing)
                if 0 not in self._computing:
                    self._computing.add(0)
                    future = self._executor.submit(self._compute_and_store_chunk, 0)
                    self._futures[0] = future

        # Schedule surrounding chunks (background)
        self._ensure_surrounding_chunks(0)

    # ------------- public API ------------- #

    def positions_at(self, t_days: float) -> np.ndarray:
        """
        Returns the heliocentric positions of all planets at time t_days (days since J2000)
        Uses cubic Hermite interpolation inside the appropriate chunk.
        If the required chunk is not ready yet, returns clamped positions from the
        nearest available chunk to avoid blocking the GUI.
        """
        if t_days < 0:
            t = 0.0
        else:
            t = float(t_days)

        if self.max_days is not None and t > self.max_days:
            t = self.max_days

        chunk_index = self._chunk_index_for_time(t)
        # ensure desired surrounding chunks are scheduled/loaded (non-blocking)
        self._ensure_surrounding_chunks(chunk_index)

        # If chunk is ready, return interpolated positions
        with self._lock:
            chunk = self._cache.get(chunk_index)

        if chunk is not None:
            return chunk.positions_at(t)

        # Chunk not ready: fallback to nearest available cached chunk (clamped)
        with self._lock:
            if not self._cache:
                # No chunks available at all -> return zeros as a final fallback.
                n_planets = len(PLANET_IDS)
                return np.zeros((n_planets, 3), dtype=np.float32)

            # pick nearest cached chunk index
            available_indices = list(self._cache.keys())
            nearest = min(available_indices, key=lambda k: abs(k - chunk_index))
            chunk = self._cache[nearest]

        # Clamp the time t to the nearest chunk range and return positions
        start, end = chunk.times_days[0], chunk.times_days[-1]
        t_clamped = float(np.clip(t, start, end))
        return chunk.positions_at(t_clamped)

    # -------------- helper functions ------------- #

    def _chunk_index_for_time(self, t_days: float) -> int:
        return int(t_days // self.chunk_days)

    def _chunk_time_range(self, index: int) -> Tuple[float, float]:
        start = index * self.chunk_days
        end = (index + 1) * self.chunk_days

        if self.max_days is not None:
            end = min(end, self.max_days)

        return start, end

    def _chunk_filename(self, index: int) -> Path:
        return self.cache_dir / f"chunk_{index:04d}_y{self.chunk_years:g}.npz"

    def _ensure_chunk_ready(self, index: int, sync: bool = False) -> None:
        """
        Ensure the given chunk is either loaded or scheduled for compute.
        If sync is True and no file exists, compute it synchronously (not used by default).
        """
        if index < 0:
            return

        fname = self._chunk_filename(index)
        if fname.exists():
            try:
                data = np.load(fname)
                chunk = EphemerisChunk(
                    index=index,
                    times_days=data["times_days"],
                    positions=data["positions"],
                    velocities=data["velocities"],
                )
                with self._lock:
                    self._cache[index] = chunk
                return
            except Exception:
                # If file is corrupted, remove and recompute
                try:
                    fname.unlink()
                except Exception:
                    pass

        # file doesn't exist -> compute (sync or schedule)
        if sync:
            chunk = self._compute_chunk(index)
            if chunk is not None:
                with self._lock:
                    self._cache[index] = chunk
            return

        # schedule background compute if not already computing
        with self._lock:
            if index in self._computing:
                return
            self._computing.add(index)
            future = self._executor.submit(self._compute_and_store_chunk, index)
            self._futures[index] = future

    def _ensure_surrounding_chunks(self, center_index: int) -> None:
        """
        Make sure previous, current, and next chunks are loaded or scheduled.
        """
        indices = {center_index}
        prev_idx = center_index - 1
        next_idx = center_index + 1

        if prev_idx >= 0:
            indices.add(prev_idx)

        if self.max_days is None:
            indices.add(next_idx)
        else:
            start, _ = self._chunk_time_range(next_idx)
            if start <= self.max_days:
                indices.add(next_idx)

        for idx in sorted(indices):
            self._ensure_chunk_ready(idx)

        # Enforce an in-memory cache size limit (remove farthest chunks)
        with self._lock:
            if len(self._cache) > self.max_chunk_in_memory:
                keys = list(self._cache.keys())
                keys.sort(key=lambda k: abs(k - center_index), reverse=True)
                for k in keys[self.max_chunk_in_memory:]:
                    self._cache.pop(k, None)

    def _compute_and_store_chunk(self, index: int) -> None:
        """
        Background worker wrapper that computes a chunk and stores it in the cache and file.
        """
        try:
            chunk = self._compute_chunk(index)
            if chunk is None:
                return
            fname = self._chunk_filename(index)
            np.savez_compressed(
                fname,
                times_days=chunk.times_days,
                positions=chunk.positions,
                velocities=chunk.velocities,
            )
            with self._lock:
                self._cache[index] = chunk
        finally:
            with self._lock:
                self._computing.discard(index)
                self._futures.pop(index, None)

    def _compute_chunk(self, index: int) -> Optional[EphemerisChunk]:
        """
        Compute a single chunk synchronously (heavy CPU operation).
        Returns EphemerisChunk or None (if index invalid).
        """
        if index < 0:
            return None

        if self.max_days is not None:
            start_days, end_days = self._chunk_time_range(index)
            if start_days > self.max_days:
                return None
        else:
            start_days, end_days = self._chunk_time_range(index)

        print(f"Computing ephemeris chunk {index} ({start_days:.1f}-{end_days:.1f} days since J2000) ...")

        times_days = np.arange(
            start_days,
            end_days + 1e-6,
            self.step_days,
            dtype=float,
        )

        n_steps = len(times_days)
        planet_ids = list(PLANET_IDS.values())
        n_planets = len(planet_ids)

        positions = np.zeros((n_planets, n_steps, 3), dtype=np.float32)
        velocities = np.zeros_like(positions)

        for j, t_days in enumerate(times_days):
            current_dt = J2000_DATETIME + timedelta(days=float(t_days))
            y, m, d = current_dt.year, current_dt.month, current_dt.day
            H, Min, S = current_dt.hour, current_dt.minute, current_dt.second

            for i, pid in enumerate(planet_ids):
                # Orbits function -- expected to be CPU-only (no networking)
                r_vec, v_vec = of.date_to_planet_rv(pid, y, m, d, H, Min, S)

                r = np.asarray(r_vec, dtype=np.float32)
                v = np.asarray(v_vec, dtype=np.float32)

                # Convert to AU and AU/day
                positions[i, j, :] = r / AU_KM
                velocities[i, j, :] = v * (SECONDS_PER_DAY / AU_KM)

        print(f"Finished computing chunk {index} (saved to file).")
        return EphemerisChunk(
            index=index,
            times_days=times_days,
            positions=positions,
            velocities=velocities,
        )

    def shutdown(self) -> None:
        """Shutdown the background executor cleanly (call on program exit)."""
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass