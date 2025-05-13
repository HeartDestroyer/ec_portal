"""Изменение типа old_id в таблице User

Revision ID: d20049f54108
Revises: 01a36e1bddcc
Create Date: 2025-05-13 17:08:21.672219
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd20049f54108'
down_revision: Union[str, None] = '01a36e1bddcc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Шаг 1: Создать временную таблицу для сохранения UUID
    op.execute("""
        CREATE TABLE temp_old_id_map (
            new_id INTEGER PRIMARY KEY,
            old_uuid UUID
        )
    """)
    
    # Шаг 2: Добавить временный столбец для новых целочисленных ID
    op.add_column('users', sa.Column('temp_old_id', sa.Integer(), nullable=True))
    
    # Шаг 3: Создать последовательность
    op.execute("CREATE SEQUENCE IF NOT EXISTS users_old_id_seq")
    
    # Шаг 4: Заполнить temp_old_id и сохранить соответствие UUID
    op.execute("""
        INSERT INTO temp_old_id_map (new_id, old_uuid)
        SELECT nextval('users_old_id_seq'), old_id
        FROM users
        WHERE old_id IS NOT NULL
    """)
    op.execute("""
        UPDATE users
        SET temp_old_id = (SELECT new_id FROM temp_old_id_map WHERE old_uuid = users.old_id)
        WHERE old_id IS NOT NULL
    """)
    
    # Шаг 5: Удалить старый столбец old_id
    op.drop_column('users', 'old_id')
    
    # Шаг 6: Переименовать temp_old_id в old_id
    op.alter_column('users', 'temp_old_id', new_column_name='old_id')

def downgrade() -> None:
    # Шаг 1: Добавить временный столбец для UUID
    op.add_column('users', sa.Column('temp_old_id', sa.UUID(), nullable=True))
    
    # Шаг 2: Восстановить оригинальные UUID из temp_old_id_map
    op.execute("""
        UPDATE users
        SET temp_old_id = (SELECT old_uuid FROM temp_old_id_map WHERE new_id = users.old_id)
        WHERE old_id IS NOT NULL
    """)
    
    # Шаг 3: Удалить столбец old_id
    op.drop_column('users', 'old_id')
    
    # Шаг 4: Переименовать temp_old_id в old_id
    op.alter_column('users', 'temp_old_id', new_column_name='old_id')
    
    # Шаг 5: Удалить временную таблицу и последовательность
    op.execute("DROP TABLE temp_old_id_map")
    op.execute("DROP SEQUENCE IF EXISTS users_old_id_seq")