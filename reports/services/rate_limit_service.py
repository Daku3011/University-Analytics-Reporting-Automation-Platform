import datetime
from django.core.cache import cache
from django.conf import settings

class RateLimitService:
    @staticmethod
    def get_keys(user_id, action_prefix="gemini"):
        today = datetime.date.today()
        cooldown_key = f"{action_prefix}_cooldown_{user_id}"
        limit_key = f"{action_prefix}_limit_{user_id}_{today}"
        return cooldown_key, limit_key

    @classmethod
    def check_rate_limit(cls, user_id, action_prefix="gemini"):
        """
        Checks if the user is rate limited (either cooldown or daily limit).
        Returns (is_limited, error_html)
        """
        gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
        cooldown_key, limit_key = cls.get_keys(user_id, action_prefix)

        # Check cooldown
        if cache.get(cooldown_key):
            error_html = (
                "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
                "background:#fdf2e6;border:1px solid #f0d4b0;border-radius:6px;'>"
                "<i class='ph ph-clock' style='font-size:18px;color:#c97a2f;flex-shrink:0;margin-top:2px;'></i>"
                "<div style='font-size:13.5px;color:#7a4a1a;'><strong>AI summary skipped</strong>"
                " &mdash; Please wait 60 seconds before generating again.</div></div>"
            )
            return True, error_html

        # Check daily limit
        daily_count = cache.get(limit_key, 0)
        daily_limit = gemini_config.get('DAILY_LIMIT', 50)
        if daily_count >= daily_limit:
            error_html = (
                "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
                "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
                "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
                f"<div style='font-size:13.5px;color:#7a2a22;'><strong>Daily limit reached</strong>"
                f" &mdash; {daily_limit} AI summaries used today. Resets at midnight.</div></div>"
            )
            return True, error_html

        return False, None

    @classmethod
    def record_success(cls, user_id, action_prefix="gemini"):
        """Increments the rate limit count and sets the cooldown timer."""
        gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
        cooldown_key, limit_key = cls.get_keys(user_id, action_prefix)

        cooldown_secs = gemini_config.get('COOLDOWN_SECONDS', 60)
        cache.set(cooldown_key, True, cooldown_secs)
        
        daily_count = cache.get(limit_key, 0)
        cache.set(limit_key, daily_count + 1, 86400) # Expire in 1 day
