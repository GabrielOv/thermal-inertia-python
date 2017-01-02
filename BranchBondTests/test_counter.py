def counter(fn):
    def _counted(*largs, **kargs):
        _counted.invocations += 1
        fn(*largs, **kargs)
    _counted.invocations = 0
    return _counted

def test():
    print( "Hello")

test = counter(test)
test()
test()
test()
test()

print(test.invocations)
