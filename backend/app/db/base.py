from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    from app.models import Organization, PlatformAccount, Role, SocialContent, SponsorshipDeal, User, WorkspaceAlert

    _ = (Organization, PlatformAccount, Role, SocialContent, SponsorshipDeal, User, WorkspaceAlert)