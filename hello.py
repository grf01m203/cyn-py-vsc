# hello.py git test
def hello():
    print("Hello Git + VSCode")
    print("Hello, World!")
    print("Modified on Gitee Web")
    print("Edit from Gitee website")
    print("Edit from GitHub website")
def prints_1():
    print("  ")
def jjf():
    a=10
    b=30
    c=a*b
    print(f"Result of {a} * {b} = {c}")
def power_tower(base, times):
    """幂塔函数 base^base^base... 共times层"""
    if times == 0:
        return 1
    res = base
    for i in range(times - 1):
        res = base ** res
    return res
def add(a,b):
    return a+b

if __name__ == "__main__":
    hello()
    prints_1()
    jjf()
    print(power_tower(2,3))
    #2^(2^2)=16
    #test
    print("This change comes from second device (B)")
    print(add(10,20))
    #B协助