# app/models.py
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from slugify import slugify # pip install python-slugify

# --- MODELL FÖR ROLLER ---
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    def __repr__(self): return f'<Role {self.name}>'

# --- USER MODELL ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(120), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', backref=db.backref('users', lazy='dynamic'), lazy='joined')
    support_tickets = db.relationship('SupportTicket', backref='user', lazy='dynamic')
    edited_wiki_pages = db.relationship('WikiPage', foreign_keys='WikiPage.editor_id', backref='editor', lazy='dynamic')
    wiki_revisions = db.relationship('WikiRevision', foreign_keys='WikiRevision.editor_id', backref='editor', lazy='dynamic')
    forum_threads = db.relationship('ForumThread', backref='author', lazy='dynamic', foreign_keys='ForumThread.author_id')
    forum_posts = db.relationship('ForumPost', backref='author', lazy='dynamic', foreign_keys='ForumPost.author_id')
    # last_forum_posts backref behövs ej

    def set_password(self, password): from app import bcrypt; self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    def check_password(self, password): from app import bcrypt; return bcrypt.check_password_hash(self.password_hash, password)
    def __repr__(self): role_name = self.role.name if self.role else "Ingen roll"; return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{role_name}')>"
    def is_moderator(self): return self.role and (self.role.name == 'Moderator' or self.role.name == 'Admin')
    def is_admin(self): return self.role and self.role.name == 'Admin'

# --- Funktion för Flask-Login ---
@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))

# --- Support Ticket Modell ---
class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='new', nullable=False)
    def __repr__(self): return f'<SupportTicket {self.id} Subject: {self.subject}>'

# --- Wiki Page Modell ---
class WikiPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_modified_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    editor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    revisions = db.relationship('WikiRevision', backref='page', lazy='dynamic', cascade='all, delete-orphan')
    def __repr__(self): return f'<WikiPage id={self.id} slug=\'{self.slug}\' title=\'{self.title}\'>'

# --- Wiki Revision Modell ---
class WikiRevision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('wiki_page.id'), nullable=False)
    editor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    comment = db.Column(db.String(255), nullable=True)
    def __repr__(self): editor_name = self.editor.username if self.editor else 'Okänd'; return f'<WikiRevision id={self.id} page_id={self.page_id} editor={editor_name} time={self.timestamp}>'

# --- Forum Category Modell ---
class ForumCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    threads = db.relationship('ForumThread', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    @staticmethod
    def generate_slug(target, value, oldvalue, initiator):
        if value and (not target.slug or value != oldvalue): target.slug = slugify(value)
    def __repr__(self): return f'<ForumCategory {self.name}>'
db.event.listen(ForumCategory.name, 'set', ForumCategory.generate_slug, retval=False)

# --- Forum Thread Modell (med korrekt 'posts' relation) ---
class ForumThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    last_post_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('forum_category.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # --- KORRIGERAD RELATION TILL POSTS ---
    posts = db.relationship(
        'ForumPost', # Målklassens namn (sträng)
        backref='thread',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ForumPost.created_at',
        foreign_keys='ForumPost.thread_id' # Talar om att denna relation använder ForumPost.thread_id
    )
    # --- SLUT KORRIGERAD RELATION ---

    # Fält för senaste inlägg
    last_post_id = db.Column(db.Integer, db.ForeignKey('forum_post.id'), nullable=True)
    last_poster_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationer för senaste inlägg/postare
    last_post = db.relationship('ForumPost', foreign_keys=[last_post_id])
    last_poster = db.relationship('User', foreign_keys=[last_poster_id])

    def __repr__(self): return f'<ForumThread {self.title}>'

# --- Forum Post Modell ---
class ForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Denna FK används av 'posts'-relationen ovan
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_thread.id'), nullable=False)

    def __repr__(self): return f'<ForumPost id={self.id} by {self.author.username if self.author else "?"}>'