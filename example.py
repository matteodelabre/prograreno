from prograreno.containedprocess import ContainedProcess
from time import sleep
from random import randrange


child = ContainedProcess(
    ['/usr/bin/python3', 'double.py'],
    root='rootfs',
    mount='child',
    memory_limit=50_000_000,
)

child.start()

try:
    while True:
        query = randrange(100)
        print("parent:", query)
        print(query, file=child.stdin)

        answer = child.stdout.readline()

        if not answer:
            break

        print("child:", int(answer))
        print()
        sleep(1)
except KeyboardInterrupt:
    pass

child.stop()
