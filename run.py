from app import create_app, db
from app.models import User , SupportTicket# Importera dina modeller
# Importera andra modeller vid behov här (SupportTicket etc.)

from commands import seed_roles_command # Justera om du använde en grupp

app = create_app()

app.cli.add_command(seed_roles_command)
# Detta gör att du kan köra `flask shell` och ha `app` och `db` tillgängliga
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'SupportTicket': SupportTicket} # Lägg till modeller här

if __name__ == '__main__':
    # Kör inte app.run() i produktion med CloudPanel, använd WSGI-server (Gunicorn)
    # Detta är bara för lokal utveckling
    app.run(debug=True) # debug=True ska vara False i produktion