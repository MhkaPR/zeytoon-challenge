"""Public runtime configuration shared with the frontend (Principle XIII).

Values live in django-constance so operators can change them from the settings interface
without a redeploy. The public site fetches this payload once on load.
"""

from constance import config


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _number_list(value, default):
    if not isinstance(value, (list, tuple)):
        return list(default)
    result = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result or list(default)


def _resource_options(value):
    defaults = {
        "ram": [1, 2, 4, 8, 16, 32, 64],
        "cpu": [1, 2, 4, 8, 16],
        "disk": [20, 50, 100, 250, 500, 1000],
        "traffic": [100, 500, 1000, 2000, 5000, 10000],
    }
    raw = value if isinstance(value, dict) else {}
    return {
        key: _number_list(raw.get(key), default)
        for key, default in defaults.items()
    }


def public_site_config():
    """Return the frontend-facing configuration payload."""
    return {
        "catalog": {
            "priceMin": _int(config.CATALOG_PRICE_MIN, 300000),
            "priceMax": _int(config.CATALOG_PRICE_MAX, 1500000),
            "priceStep": _int(config.CATALOG_PRICE_STEP, 50000),
            "pageSizes": _number_list(config.CATALOG_PAGE_SIZES, [8, 12]),
            "defaultPageSize": _int(config.CATALOG_PAGE_SIZE_DEFAULT, 8),
            "resourceOptions": _resource_options(config.CATALOG_RESOURCE_OPTIONS),
            "companyFilterVisible": _int(
                config.CATALOG_COMPANY_FILTER_VISIBLE, 5
            ),
        },
        "ops": {
            "siteRefreshMs": _int(config.OPS_SITE_REFRESH_MS, 8000),
            "linksRefreshMs": _int(config.OPS_LINKS_REFRESH_MS, 5000),
            "captureDefaultDurationMs": _int(config.CAPTURE_FIXED_DURATION_MS, 15000),
        },
        "contact": {
            "email": str(config.CONTACT_EMAIL),
            "phone": str(config.CONTACT_PHONE),
            "address": str(config.CONTACT_ADDRESS),
        },
        "social": {
            "instagram": str(config.SOCIAL_INSTAGRAM_URL),
            "telegram": str(config.SOCIAL_TELEGRAM_URL),
            "linkedin": str(config.SOCIAL_LINKEDIN_URL),
            "github": str(config.SOCIAL_GITHUB_URL),
        },
    }


def settings_snapshot():
    """Flat constance values exposed in the operator settings interface."""
    return {
        "CATALOG_PRICE_MIN": _int(config.CATALOG_PRICE_MIN, 300000),
        "CATALOG_PRICE_MAX": _int(config.CATALOG_PRICE_MAX, 1500000),
        "CATALOG_PRICE_STEP": _int(config.CATALOG_PRICE_STEP, 50000),
        "CATALOG_PAGE_SIZES": _number_list(config.CATALOG_PAGE_SIZES, [8, 12, 20]),
        "CATALOG_PAGE_SIZE_DEFAULT": _int(config.CATALOG_PAGE_SIZE_DEFAULT, 8),
        "CATALOG_RESOURCE_OPTIONS": _resource_options(
            config.CATALOG_RESOURCE_OPTIONS
        ),
        "CATALOG_COMPANY_FILTER_VISIBLE": _int(
            config.CATALOG_COMPANY_FILTER_VISIBLE, 5
        ),
        "OPS_SITE_REFRESH_MS": _int(config.OPS_SITE_REFRESH_MS, 8000),
        "OPS_LINKS_REFRESH_MS": _int(config.OPS_LINKS_REFRESH_MS, 5000),
        "CAPTURE_FIXED_DURATION_MS": _int(config.CAPTURE_FIXED_DURATION_MS, 15000),
        "CONTACT_EMAIL": str(config.CONTACT_EMAIL),
        "CONTACT_PHONE": str(config.CONTACT_PHONE),
        "CONTACT_ADDRESS": str(config.CONTACT_ADDRESS),
        "SOCIAL_INSTAGRAM_URL": str(config.SOCIAL_INSTAGRAM_URL),
        "SOCIAL_TELEGRAM_URL": str(config.SOCIAL_TELEGRAM_URL),
        "SOCIAL_LINKEDIN_URL": str(config.SOCIAL_LINKEDIN_URL),
        "SOCIAL_GITHUB_URL": str(config.SOCIAL_GITHUB_URL),
    }
