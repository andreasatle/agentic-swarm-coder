from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

class TaskTimerError(Exception):
    """Custom exception for TaskTimer operations."""
    pass

class TaskTimer:
    """
    Multi-task timer with JSON persistence, injectable time provider, and load/save state.
    """
    def __init__(self, state_file: Optional[str] = None, time_provider: Callable[[], float] = time.time):
        self._tasks: Dict[str, Dict[str, Any]] = {}  # {task: {'start_time', 'elapsed', 'running'}}
        self._state_file = state_file
        self._time_provider = time_provider
        if state_file:
            self.load_state(state_file)

    def start(self, task: str = 'default') -> None:
        tsk = self._tasks.setdefault(task, {'start_time': None, 'elapsed': 0.0, 'running': False})
        if tsk['running']:
            raise TaskTimerError(f"Timer for task '{task}' already running.")
        tsk['start_time'] = self._time_provider()
        tsk['running'] = True
        self.save_state(self._state_file)

    def stop(self, task: str = 'default') -> None:
        tsk = self._tasks.get(task)
        if not tsk or not tsk['running']:
            raise TaskTimerError(f"Timer for task '{task}' not running.")
        end_time = self._time_provider()
        tsk['elapsed'] += end_time - tsk['start_time']
        tsk['start_time'] = None
        tsk['running'] = False
        self.save_state(self._state_file)

    def to_report(self, task: str = 'default', *, output_format: str = "table") -> str:
        tsk = self._tasks.get(task, {'start_time': None, 'elapsed': 0.0, 'running': False})
        elapsed = tsk['elapsed']
        if tsk['running'] and tsk['start_time'] is not None:
            elapsed += self._time_provider() - tsk['start_time']
        seconds = int(elapsed)
        minutes = seconds // 60
        hours = minutes // 60
        seconds = seconds % 60
        minutes = minutes % 60
        data = {
            'task': task,
            'total_seconds': int(elapsed),
            'elapsed': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            'running': tsk['running'],
        }
        if output_format == "json":
            return json.dumps(data)
        else:
            hdr = f"{'Task':<12} {'Status':<10} {'Elapsed':<10} {'Seconds':<10}"
            row = f"{task:<12} {'Running' if tsk['running'] else 'Stopped':<10} {data['elapsed']:<10} {data['total_seconds']:<10}"
            return f"{hdr}\n{row}"

    def save_state(self, path: Optional[str] = None) -> None:
        if not path:
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        state = {'tasks': self._tasks}
        try:
            with target.open('w', encoding='utf-8') as handle:
                json.dump(state, handle)
        except OSError as exc:
            raise TaskTimerError(f"Failed to save timer state to {path}: {exc}") from exc

    def load_state(self, path: Optional[str] = None) -> None:
        if not path:
            return
        try:
            with Path(path).open('r', encoding='utf-8') as handle:
                state = json.load(handle)
        except FileNotFoundError:
            self._tasks = {}
            return
        except json.JSONDecodeError as exc:
            raise TaskTimerError(f"State file {path} is corrupted: {exc}") from exc
        except OSError as exc:
            raise TaskTimerError(f"Failed to read timer state from {path}: {exc}") from exc

        tasks = state.get('tasks', {})
        if not isinstance(tasks, dict):
            raise TaskTimerError(f"State file {path} contains invalid task data.")
        self._tasks = tasks
