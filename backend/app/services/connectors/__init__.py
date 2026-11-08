from app.services.connectors.facebook import FacebookConnector
from app.services.connectors.github import GitHubConnector
from app.services.connectors.instagram import InstagramConnector
from app.services.connectors.linkedin import LinkedInConnector
from app.services.connectors.tiktok import TikTokConnector
from app.services.connectors.youtube import YouTubeConnector

CONNECTORS = {
    "youtube": YouTubeConnector,
    "instagram": InstagramConnector,
    "linkedin": LinkedInConnector,
    "github": GitHubConnector,
    "tiktok": TikTokConnector,
    "facebook": FacebookConnector,
}

__all__ = [
    "CONNECTORS",
    "InstagramConnector",
    "YouTubeConnector",
    "LinkedInConnector",
    "GitHubConnector",
    "TikTokConnector",
    "FacebookConnector",
]
