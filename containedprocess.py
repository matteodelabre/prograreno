import sys
sys.path = ['/usr/local/lib/python3.10/site-packages'] + sys.path

import python_crun
from uuid import uuid4
import json
import os
from pathlib import Path


class ContainedProcess:
    __slots__ = ['id', 'spec', 'running', 'context', 'stdin', 'stdout']

    def __init__(
        self,
        root: str,
        mount: str,
        args: list[str],
        memory_limit: int = -1,
    ):
        program_mount = '/x'
        self.id = str(uuid4())

        self.spec = json.loads(python_crun.spec())
        self.spec['root'] = {
            'path': Path(root).absolute().as_posix(),
            'readonly': True,
        }
        self.spec['process'] = {
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
        self.spec['mounts'].append(
            {
                'destination': program_mount,
                'source': Path(mount).absolute().as_posix(),
                'options': ['rbind', 'ro'],
                'type': 'none',
            }
        )

        self.running = False
        self.context = None
        self.stdin = None
        self.stdout = None

    def start(self):
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
        c_spec = python_crun.load_from_memory(json.dumps(self.spec))
        self.context = python_crun.make_context(self.id, detach=True)
        python_crun.run(self.context, c_spec)

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
        if not self.running:
            return

        self.running = False
        self.stdin.close()
        self.stdin = None
        self.stdout.close()
        self.stdout = None

        python_crun.delete(self.context, self.id, True)
        self.context = None
