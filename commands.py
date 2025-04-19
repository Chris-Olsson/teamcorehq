# commands.py
import click
from flask.cli import with_appcontext
from app import db
from app.models import Role

# Definiera en kommandogrupp (valfritt men bra för organisation)
# @click.group()
# def seed_cli():
#     pass

@click.command('seed-roles') # Kommandot blir 'flask seed-roles'
@with_appcontext # Ger tillgång till app-kontexten (db, etc.)
def seed_roles_command():
    """Skapar initiala användarroller i databasen."""
    roles_to_add = [
        {'name': 'Member', 'description': 'Standard user role'},
        {'name': 'Moderator', 'description': 'Can manage users and content'},
        {'name': 'Admin', 'description': 'Full administrative access'},
    ]
    added_count = 0
    skipped_count = 0

    for role_data in roles_to_add:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(name=role_data['name'], description=role_data.get('description'))
            db.session.add(role)
            print(f"Adding role: {role_data['name']}")
            added_count += 1
        else:
            print(f"Skipping role (already exists): {role_data['name']}")
            skipped_count += 1

    if added_count > 0:
        try:
            db.session.commit()
            print(f"Successfully added {added_count} role(s).")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing roles: {e}")
    else:
        print("No new roles to add.")

    if skipped_count > 0:
         print(f"Skipped {skipped_count} role(s) that already existed.")

# Lägg till kommandot till gruppen (om du använder en grupp)
# seed_cli.add_command(seed_roles_command)