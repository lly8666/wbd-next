import sys
import m0_h2464_capacity as c
import m0_h2228_three_runner_relay as h
if __name__=="__main__":
    if sys.argv[1]=="control-serve":c.relay()
    else:h.main()
