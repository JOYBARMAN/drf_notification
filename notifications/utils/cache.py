from django.conf import settings
from django.core.cache import cache


# Get the cache timeout (timeout default is 5 days)
CACHE_TIMEOUT = getattr(settings, "CACHE_TIMEOUT", 432000)


def generate_sub_key(query_params, page_number):
    """Generate a sub-key based on the query parameters and page number"""
    return f"{query_params}_{page_number}"


def get_user_cache_notifications(user, query_params, page_number):
    """Get the user's notifications from the cache"""
    cache_key = user.id

    # Fetch the cached data for the user
    user_cache = cache.get(cache_key, {})

    sub_key = generate_sub_key(query_params, page_number)

    # Try to get the cached data from the user's cache
    if user_cache.get(sub_key):
        return user_cache[sub_key]

    return None


def set_user_notifications_in_cache(user, query_params, page_number, queryset):
    """Cache the user's notifications"""
    user_cache = cache.get(user.id, {})

    sub_key = generate_sub_key(query_params, page_number)

    # Cache the queryset
    user_cache[sub_key] = queryset
    cache.set(user.id, user_cache, CACHE_TIMEOUT)

    return
