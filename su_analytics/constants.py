"""
Shared constants for the SU Analytics platform.

Centralizes choices that were previously duplicated across
accounts, analytics_app, events, and reports models.
"""
import datetime


def _current_year():
    """Dynamic default for year fields — avoids hardcoded 2026."""
    return datetime.date.today().year


MONTH_CHOICES = [
    (1, 'January'), (2, 'February'), (3, 'March'),
    (4, 'April'), (5, 'May'), (6, 'June'),
    (7, 'July'), (8, 'August'), (9, 'September'),
    (10, 'October'), (11, 'November'), (12, 'December'),
]

QUARTER_CHOICES = [
    (1, 'Q1 (Jan–Mar)'),
    (2, 'Q2 (Apr–Jun)'),
    (3, 'Q3 (Jul–Sep)'),
    (4, 'Q4 (Oct–Dec)'),
]

QUARTER_MONTHS = {
    1: ('January', 'February', 'March'),
    2: ('April',   'May',      'June'),
    3: ('July',    'August',   'September'),
    4: ('October', 'November', 'December'),
}

QUARTER_LABELS = {
    1: 'January–March',
    2: 'April–June',
    3: 'July–September',
    4: 'October–December',
}

EVENT_CATEGORY_CHOICES = [
    ('workshop', 'Workshop'),
    ('festival', 'Festival'),
    ('placement', 'Placement'),
    ('achievement', 'Achievement'),
    ('conference', 'Conference'),
    ('guest_lecture', 'Guest Lecture'),
    ('academic', 'Academic Event'),
    ('cultural', 'Cultural Event'),
    ('sports', 'Sports Event'),
    ('other', 'Other'),
]

PLATFORM_CHOICES = [
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
]

MEDIA_TYPE_CHOICES = [
    ('image', 'Image'),
    ('video', 'Video'),
    ('pdf', 'PDF'),
    ('reel', 'Reel'),
    ('poster', 'Poster'),
]

ROLE_CHOICES = [
    ('super_admin', 'Super Admin'),
    ('college_admin', 'College Admin'),
    ('analytics_team', 'Analytics Team'),
]

# Analytics keys used in report comparisons
ANALYTICS_KEYS = [
    'total_views', 'total_reach', 'followers_gained',
    'instagram_views', 'facebook_views',
    'instagram_reach', 'facebook_reach',
    'reels_count', 'graphics_count',
    'youtube_subscribers', 'instagram_followers', 'facebook_followers',
]
