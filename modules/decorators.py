import time
from functools import wraps
from threading import Lock

def rate_limit(max_calls, period):
    def decorator(func):
        last_reset = [time.time()]  # Using a list to allow access to the nonlocal variable in closures
        call_count = [0]
        lock = Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()

                # Calculate the time since the last reset
                time_since_reset = current_time - last_reset[0]

                # If the period has elapsed, reset the rate limit counter
                if time_since_reset >= period:
                    last_reset[0] = current_time
                    call_count[0] = 0

                # If the call count is within the limit, proceed
                if call_count[0] < max_calls:
                    call_count[0] += 1
                    return func(*args, **kwargs)
                else:
                    # Calculate how long to wait before retrying
                    time_to_wait = period - time_since_reset
                    time.sleep(time_to_wait)
                    # After sleeping, reset the counter and timestamp
                    last_reset[0] = time.time()
                    call_count[0] = 1  # Set to 1 because it's about to make a call
                    return func(*args, **kwargs)

        return wrapper

    return decorator

def rate_limit_old(max_calls, period):
    def decorator(func):
        last_reset = [time.time()]  # Using a list to allow access to the nonlocal variable in closures
        call_count = [0]
        lock = Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                current_time = time.time()
                # Reset the rate limit counter periodically
                if current_time - last_reset[0] >= period:
                    last_reset[0] = current_time
                    call_count[0] = 0

                if call_count[0] < max_calls:
                    call_count[0] += 1
                    return func(*args, **kwargs)
                else:
                    time_to_wait = period - (current_time - last_reset[0])
                    print(f"Rate limit exceeded. Try again in {time_to_wait:.2f} seconds.")
                    time.sleep(time_to_wait)
                    return wrapper(*args, **kwargs)

        return wrapper

    return decorator
