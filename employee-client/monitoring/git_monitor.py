"""
git_monitor.py

Polls configured Git repositories using GitPython and emits git_commit /
git_branch_changed events.

GitPython has no push-based event stream equivalent to watchdog, so this
monitor periodically polls each repository's HEAD state.

Design decision (finalized): the current commit hash and branch of each
repository are recorded as a baseline on startup and do NOT generate an
event. Only changes observed after initialization are reported.
"""

import threading

from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError

from monitoring.common import make_event


class GitMonitor(threading.Thread):
    def __init__(self, config: dict, event_queue, poll_interval: float = 10.0):
        super().__init__(name="GitMonitor", daemon=True)
        self.event_queue = event_queue
        self.poll_interval = poll_interval

        self._repo_paths = config.get("git_repositories", [])
        self._stop_event = threading.Event()

        # repo_path -> {"repo": Repo, "branch": str, "commit": str or None}
        self._state = {}

    @staticmethod
    def _repo_name(path: str) -> str:
        return path.rstrip("/\\").replace("\\", "/").split("/")[-1]

    @staticmethod
    def _current_branch(repo: Repo) -> str:
        try:
            return repo.active_branch.name
        except TypeError:
            # Detached HEAD state.
            return "HEAD"

    def _open_repos(self):
        """Open each configured repo and record its baseline state."""
        for path in self._repo_paths:
            try:
                repo = Repo(path)
            except (InvalidGitRepositoryError, NoSuchPathError):
                print(f"[GitMonitor] Skipping invalid repository path: {path}")
                continue

            branch = self._current_branch(repo)
            try:
                commit = repo.head.commit.hexsha
            except (ValueError, GitCommandError):
                commit = None

            self._state[path] = {"repo": repo, "branch": branch, "commit": commit}

    def _check_repo(self, path: str):
        state = self._state.get(path)
        if state is None:
            return
        repo = state["repo"]

        try:
            current_branch = self._current_branch(repo)
            current_commit = repo.head.commit.hexsha
        except (ValueError, GitCommandError):
            return

        if current_branch != state["branch"]:
            self.event_queue.put(
                make_event(
                    event_type="git_branch_changed",
                    source="gitpython",
                    data={
                        "repository": self._repo_name(path),
                        "previous_branch": state["branch"],
                        "branch": current_branch,
                    },
                )
            )
            state["branch"] = current_branch

        if current_commit != state["commit"]:
            commit_obj = repo.head.commit
            self.event_queue.put(
                make_event(
                    event_type="git_commit",
                    source="gitpython",
                    data={
                        "repository": self._repo_name(path),
                        "branch": current_branch,
                        "commit_hash": current_commit,
                        "message": commit_obj.message.strip(),
                        "author": str(commit_obj.author),
                        "commit_time": commit_obj.committed_datetime.isoformat(),
                    },
                )
            )
            state["commit"] = current_commit

    def run(self):
        self._open_repos()

        while not self._stop_event.is_set():
            for path in list(self._state.keys()):
                self._check_repo(path)
            self._stop_event.wait(self.poll_interval)

    def stop(self):
        self._stop_event.set()
