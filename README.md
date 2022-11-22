# prograreno

Run code in contained subprocesses and communicate on standard streams.

## Dependencies

* `crun` ⩾ 1.7 needs to be installed (on Arch Linux, `pacman -S crun`).

To run the example below, a working chroot must be available under the `rootfs` directory in this repository.
For example, to build a Debian chroot (on Arch Linux, run `pacman -S deboostrap` first):
```console
# sudo debootstrap --include=python3 sid ./rootfs
# mkdir ./rootfs/x
```

## Example

`example.py` sends numbers to a subprocess, which outputs twice their value back to the parent process. Here’s a sample output:
```console
$ python example.py
parent: 92
child: 184

parent: 91
child: 182

parent: 10
child: 20

parent: 86
child: 172
```
