# Hive Dead Code & Legacy Report

During the repository refactoring, files were classified into four categories to ensure clean package design and safe archival.

## 1. ACTIVE_CORE
Files moved into the `hive/` package and currently driving the engine:
- `hive/core/cortex.py`
- `hive/core/nucleus.py`
- `hive/core/dag.py`
- `hive/core/context.py`
- `hive/core/validator.py`
- `hive/runtime/reservoir.py`
- `hive/runtime/signals.py`
- `hive/adaptation/reflex_engine.py`
- `hive/adaptation/oracle.py`
- `hive/memory/hippocampus.py`
- `hive/memory/consolidator.py`
- `hive/memory/verifier.py`
- `hive/warm_cells/*`

## 2. EXPERIMENTAL
Files actively used for stress testing, benchmarks, and proving invariants. Preserved actively.
- `benchmarks/benchmark_z_mini.py`
- `tests/test_reservoir.py`
- `experiments/phase_e/test_e_verified.py`

## 3. LEGACY_ARCHIVE
Historical files that demonstrate earlier architectural epochs. These were found to have a reference count of 0 inside the `ACTIVE_CORE` but hold massive historical/research value. Moved safely into `experiments/legacy/`.
- `alpha.py`: Replaced by Nucleus Executor.
- `bin.py`: Replaced by Hippocampus + Memory Cells.
- `gatherer.py`: Replaced by Reflex Engine + Oracle.
- `labour.py`: Threadpool logic swallowed by TaskGraph/Nucleus threadpool mapping.
- `planner.py`: Replaced by Cortex Router and programmatic TaskGraphs.
- `worker.py` and `workers/`: Replaced by Hard Cells (process isolation).
- `nucleus_subprocess_cell.py`: Alpha/Phase A prototype replaced by `Reservoir`.
- `sentiment_process.py`: Moved logic into `warm_cells/`.

## 4. SAFE_DELETE
Currently, all "dead" architectural files were moved into `LEGACY_ARCHIVE` per the directive "If uncertain whether file is obsolete, archive instead of delete". 
No files were completely nuked from existence without being archived to protect the R&D notebook history.
