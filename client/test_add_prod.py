# test_add_prod.py
import time
import shared_state

print("Before:", shared_state.get_total_productive_seconds())
for i in range(5):
    shared_state.add_productive_seconds(1)
    print("Added", i+1)
    time.sleep(1)
print("After:", shared_state.get_total_productive_seconds())
