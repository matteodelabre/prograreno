try:
    while True:
        value = int(input())
        print(value * 2)
except EOFError:
    pass
