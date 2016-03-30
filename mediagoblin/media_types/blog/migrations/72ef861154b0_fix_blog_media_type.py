"""Fix blog media type

Revision ID: 72ef861154b0
Revises: 562bc42a8fff
Create Date: 2016-03-29 21:49:29.844160

"""

# revision identifiers, used by Alembic.
revision = '72ef861154b0'
down_revision = '562bc42a8fff'
branch_labels = None
depends_on = None

from alembic import op
from sqlalchemy import MetaData
from mediagoblin.db.migration_tools import inspect_table

def upgrade():
    """
    Set the correct mediatype on blog media entries.
    """
    db = op.get_bind()
    metadata = MetaData(bind=db)
    media_entries_table = inspect_table(metadata, "core__media_entries")

    # Get the media entries.
    media_entries = list(db.execute(media_entries_table.select()))

    # Iterate through all the media entries.
    for media_entry in media_entries:

        db.execute(media_entries_table.update().values(
            media_type='mediagoblin.media_types.blog'
        ).where(
            media_entries_table.c.media_type == 
                'mediagoblin.media_types.blogpost'
        ))

def downgrade():
    """
    Revert the mediatype on blog media entries.
    """
    db = op.get_bind()
    metadata = MetaData(bind=db)
    media_entries_table = inspect_table(metadata, "core__media_entries")

    # Get the media entries.
    media_entries = list(db.execute(media_entries_table.select()))

    # Iterate through all the media entries.
    for media_entry in media_entries:

        db.execute(media_entries_table.update().values(
            media_type='mediagoblin.media_types.blogpost'
        ).where(
            media_entries_table.c.media_type == 
                'mediagoblin.media_types.blog'
        ))
