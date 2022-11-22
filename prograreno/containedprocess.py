import python_crun
from uuid import uuid4
import json
import os
from pathlib import Path


class ContainedProcess:
    """Run and communicate with a subprocess in a contained environment.

    While the subprocess is running (after calling :meth:`start`), its
    standard streams can be accessed using the :param:`stdin` and
    :param:`stdout` attributes.

    :param id: Unique ID for the contained process
    :param running: True iff the container is running
    :param stdin: Standard input stream for the subprocess
    :param stdout: Standard output stream from the subprocess
    """
    __slots__ = ['id', '_spec', 'running', '_context', 'stdin', 'stdout']

    def __init__(
        self,
        args: list[str],
        root: str,
        mount: str,
        memory_limit: int = -1,
    ):
        """Initialize a contained subprocess.

        :param args: List of arguments used to spawn the process
        :param root: Root directory under which the process will be contained
        :param mount: Directory to be mounted under `/x` for the subprocess
        :param memory_limit: Maximum memory usage in bytes, or -1 for
            unlimited memory
        """
        program_mount = '/x'
        self.id = str(uuid4())

        self._spec = json.loads(python_crun.spec())
        self._spec['root'] = {
            'path': Path(root).absolute().as_posix(),
            'readonly': True,
        }
        self._spec['process'] = {
            'terminal': False,
            'cwd': program_mount,
            'args': args,
            'user': {
                'uid': 0,
                'gid': 0,
            },
            'noNewPrivileges': True,
            'rlimits': [
                {
                    'type': 'RLIMIT_AS',
                    'hard': memory_limit,
                    'soft': memory_limit,
                },
            ],
        }
        self._spec['mounts'].append(
            {
                'destination': program_mount,
                'source': Path(mount).absolute().as_posix(),
                'options': ['rbind', 'ro'],
                'type': 'none',
            }
        )

        self.running = False
        self._context = None
        self.stdin = None
        self.stdout = None

    def start(self):
        """Start the subprocess."""
        if self.running:
            return

        # Replace standard streams with pipes before forking
        (to_child_read, to_child_write) = os.pipe()
        (to_parent_read, to_parent_write) = os.pipe()

        old_stdin = os.dup(0)
        os.dup2(to_child_read, 0)

        old_stdout = os.dup(1)
        os.dup2(to_parent_write, 1)

        # Fork containerized process
        c_spec = python_crun.load_from_memory(json.dumps(self._spec))
        self._context = python_crun.make_context(self.id, detach=True)
        python_crun.run(self._context, c_spec)

        # Back to parent, restore original streams
        os.dup2(old_stdin, 0)
        os.dup2(old_stdout, 1)

        # Close unused pipe ends and initialize communication streams
        os.close(to_child_read)
        self.stdin = open(to_child_write, 'w', buffering=1)

        os.close(to_parent_write)
        self.stdout = open(to_parent_read, 'r', buffering=1)
        self.running = True

    def stop(self):
        """Stop the subprocess."""
        if not self.running:
            return

        self.running = False
        self.stdin.close()
        self.stdin = None
        self.stdout.close()
        self.stdout = None

        python_crun.delete(self._context, self.id, True)
        self._context = None
