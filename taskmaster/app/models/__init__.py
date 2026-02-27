"""
ORM model package. Import all models here so Alembic autogenerate
can discover every table through the shared Base metadata.
"""
from app.models.user import User  # noqa: F401
from app.models.team import Team, TeamMember  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.attachment import Attachment  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.activity_log import ActivityLog  # noqa: F401
