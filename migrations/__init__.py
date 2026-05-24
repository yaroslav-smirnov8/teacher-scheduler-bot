"""Database migrations package"""
from migrations.migrate_v2_recurring import migrate_v1_to_v2
from migrations.migrate_v3_feedback import migrate_v2_to_v3
from migrations.migrate_v4_homeworks import migrate_v3_to_v4
from migrations.migrate_v5_payments import migrate_v4_to_v5
from migrations.migrate_v6_unique_constraint import migrate_v5_to_v6
from migrations.migrate_v7_homework_text import migrate_v6_to_v7
from migrations.migrate_v8_json_content import migrate_v7_to_v8
from migrations.migrate_v9_attempts import migrate_v8_to_v9
from migrations.migrate_v10_payment_balance import migrate_v9_to_v10
from migrations.migrate_v11_homework_marks import migrate_v10_to_v11

MIGRATIONS = {
    1: migrate_v1_to_v2,
    2: migrate_v2_to_v3,
    3: migrate_v3_to_v4,
    4: migrate_v4_to_v5,
    5: migrate_v5_to_v6,
    6: migrate_v6_to_v7,
    7: migrate_v7_to_v8,
    8: migrate_v8_to_v9,
    9: migrate_v9_to_v10,
    10: migrate_v10_to_v11,
}
