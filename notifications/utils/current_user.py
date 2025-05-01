import threading


# Create a thread local object to store the user
_thread_locals = threading.local()


def get_current_user():
    """Get the current user from the thread local"""
    return getattr(_thread_locals, "user", None)


def set_current_user(user):
    """Set the current user in the thread local"""
    _thread_locals.user = user
