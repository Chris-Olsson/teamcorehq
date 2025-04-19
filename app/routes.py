# app/routes.py
from flask import (Blueprint, render_template, url_for, flash,
                   redirect, request, current_app, abort)
from markupsafe import Markup
from app import db, bcrypt, mail
from app.forms import (RegistrationForm, LoginForm, SupportForm, EditUserForm,
                       AdminCreateUserForm, RoleForm, WikiPageForm,
                       PostForm, NewThreadForm, ForumCategoryForm)
from app.models import (User, SupportTicket, Role, WikiPage, WikiRevision,
                        ForumCategory, ForumThread, ForumPost)
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from functools import wraps
import os
import markdown2
import datetime
from sqlalchemy.orm import joinedload

main = Blueprint('main', __name__)

# --- Helpers / Decorators ---
def moderator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator():
            flash('Du har inte behörighet att se denna sida.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Markdown-konverterare
md_converter = markdown2.Markdown(extras=['fenced-code-blocks', 'tables', 'footnotes', 'spoiler', 'strike', 'code-friendly'])

# --- Vanliga Routes ---
@main.route("/")
@main.route("/index")
def index():
    return render_template('index.html', title='Hem')

# ...(Routes för register, login, logout, support - oförändrade)...
@main.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        default_role_name = 'Member'; first_user = False
        if not User.query.first(): default_role_name = 'Moderator'; first_user = True
        user_role = Role.query.filter_by(name=default_role_name).first()
        if not user_role: flash(f'Standardrollen "{default_role_name}" kunde inte hittas!', 'danger'); return render_template('register.html', title='Registrera', form=form)
        if first_user: flash(f'Första användaren ({form.username.data}) skapad med rollen {default_role_name}!', 'info')
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, role=user_role)
        try:
            db.session.add(user); db.session.commit(); flash(f'Konto skapat för {form.username.data}! Du kan nu logga in.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod vid registrering: {e}', 'danger'); current_app.logger.error(f"Fel vid registrering: {e}")
    return render_template('register.html', title='Registrera', form=form)

@main.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data); next_page = request.args.get('next')
            flash('Inloggning lyckades!', 'success')
            return redirect(next_page) if next_page and next_page.startswith('/') else redirect(url_for('main.index'))
        else: flash('Inloggning misslyckades. Kontrollera e-post och lösenord.', 'danger')
    return render_template('login.html', title='Logga In', form=form)

@main.route("/logout")
def logout():
    logout_user(); flash('Du har loggats ut.', 'info'); return redirect(url_for('main.index'))

@main.route("/support", methods=['GET', 'POST'])
def support():
    form = SupportForm()
    if form.validate_on_submit():
        ticket = SupportTicket(email=form.email.data, subject=form.subject.data, message=form.message.data, user_id=current_user.id if current_user.is_authenticated else None)
        db.session.add(ticket); db.session.commit()
        try:
            support_recipient = current_app.config.get('SUPPORT_MAIL_RECIPIENT')
            if support_recipient:
                 msg = Message(subject=f"Supportärende: {form.subject.data}", sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[support_recipient])
                 msg.body = f"Nytt supportärende från: {form.email.data}\nAnvändare: {current_user.username if current_user.is_authenticated else 'Ej inloggad'}\n\nÄmne: {form.subject.data}\n\nMeddelande:\n{form.message.data}"
                 mail.send(msg); flash('Ditt supportärende har skickats via e-post!', 'success')
            else: flash('Supportfunktionen via e-post är inte konfigurerad.', 'warning')
        except Exception as e: current_app.logger.error(f"Kunde inte skicka supportmail: {e}"); flash('Ett fel uppstod när supportärendet skulle skickas via e-post.', 'danger')
        flash('Ditt supportärende har tagits emot (sparades i databasen).', 'success')
        return redirect(url_for('main.index'))
    elif request.method == 'GET' and current_user.is_authenticated: form.email.data = current_user.email
    return render_template('support.html', title='Support', form=form)


# --- Admin/Moderator Routes ---
# ...(admin_dashboard, edit_user, create_user, manage_roles, edit_role, manage_forum_categories, edit_forum_category, delete_forum_category - oförändrade)...
@main.route("/admin/dashboard")
@login_required
@moderator_required
def admin_dashboard():
     all_users = User.query.order_by(User.id).all(); return render_template('admin/dashboard.html', title="Moderatorpanel", users=all_users)

@main.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@moderator_required
def edit_user(user_id):
    user_to_edit = User.query.get_or_404(user_id); form = EditUserForm(original_user=user_to_edit)
    if form.validate_on_submit():
        user_to_edit.username = form.username.data; user_to_edit.email = form.email.data; user_to_edit.role = form.role.data
        try: db.session.commit(); flash(f'Uppgifterna för {user_to_edit.username} har uppdaterats.', 'success')
        except Exception as e: db.session.rollback(); flash(f'Ett oväntat fel uppstod när användaren skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid uppdatering av användare {user_id}: {e}")
        return redirect(url_for('main.admin_dashboard'))
    elif request.method == 'GET': form.username.data = user_to_edit.username; form.email.data = user_to_edit.email; form.role.data = user_to_edit.role
    return render_template('admin/edit_user.html', title='Redigera Användare', form=form, user_to_edit=user_to_edit)

@main.route('/admin/user/create', methods=['GET', 'POST'])
@login_required
@moderator_required
def create_user():
    form = AdminCreateUserForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8'); selected_role = form.role.data
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, role=selected_role)
        try:
            db.session.add(user); db.session.commit(); flash(f'Användaren {form.username.data} har skapats med rollen {selected_role.name}.', 'success')
            return redirect(url_for('main.admin_dashboard'))
        except Exception as e: db.session.rollback(); flash(f'Ett oväntat fel uppstod när användaren skulle skapas: {e}', 'danger'); current_app.logger.error(f"Fel vid skapande av användare: {e}")
    return render_template('admin/create_user.html', title='Skapa Ny Användare', form=form)

@main.route('/admin/roles', methods=['GET', 'POST'])
@login_required
@moderator_required
def manage_roles():
    form = RoleForm()
    if form.validate_on_submit():
        new_role = Role(name=form.name.data.capitalize(), description=form.description.data)
        try: db.session.add(new_role); db.session.commit(); flash(f'Rollen "{new_role.name}" har skapats.', 'success'); return redirect(url_for('main.manage_roles'))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när rollen skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid skapande av roll: {e}")
    all_roles = Role.query.order_by(Role.name).all()
    return render_template('admin/roles.html', title="Hantera Roller", roles=all_roles, form=form)

@main.route('/admin/role/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@moderator_required
def edit_role(role_id):
    role_to_edit = Role.query.get_or_404(role_id); form = RoleForm(original_role=role_to_edit)
    if form.validate_on_submit():
        role_to_edit.name = form.name.data.capitalize(); role_to_edit.description = form.description.data
        try: db.session.commit(); flash(f'Rollen "{role_to_edit.name}" har uppdaterats.', 'success'); return redirect(url_for('main.manage_roles'))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när rollen "{role_to_edit.name}" skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid redigering av roll {role_id}: {e}")
    elif request.method == 'GET': form.name.data = role_to_edit.name; form.description.data = role_to_edit.description
    return render_template('admin/edit_role.html', title="Redigera Roll", form=form, role_to_edit=role_to_edit)

@main.route('/admin/forum/categories', methods=['GET', 'POST'])
@login_required
@moderator_required
def manage_forum_categories():
    form = ForumCategoryForm()
    if form.validate_on_submit():
        new_category = ForumCategory(name=form.name.data, description=form.description.data)
        try:
            db.session.add(new_category); db.session.commit(); flash(f'Kategorin "{new_category.name}" har skapats.', 'success')
            return redirect(url_for('main.manage_forum_categories'))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när kategorin skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid skapande av forumkategori: {e}")
    categories = ForumCategory.query.order_by(ForumCategory.name).all()
    return render_template('admin/forum_categories.html', title="Hantera Forumkategorier", categories=categories, form=form)

@main.route('/admin/forum/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@moderator_required
def edit_forum_category(category_id):
    category_to_edit = ForumCategory.query.get_or_404(category_id); form = ForumCategoryForm(original_category=category_to_edit)
    if form.validate_on_submit():
        category_to_edit.name = form.name.data; category_to_edit.description = form.description.data
        try:
            db.session.commit(); flash(f'Kategorin "{category_to_edit.name}" har uppdaterats.', 'success')
            return redirect(url_for('main.manage_forum_categories'))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när kategorin "{category_to_edit.name}" skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid redigering av forumkategori {category_id}: {e}")
    elif request.method == 'GET': form.name.data = category_to_edit.name; form.description.data = category_to_edit.description
    return render_template('admin/edit_forum_category.html', title=f"Redigera Kategori: {category_to_edit.name}", form=form, category_to_edit=category_to_edit)

@main.route('/admin/forum/category/<int:category_id>/delete', methods=['POST'])
@login_required
@moderator_required
def delete_forum_category(category_id):
    category_to_delete = ForumCategory.query.get_or_404(category_id)
    if category_to_delete.threads.count() > 0:
        flash(f'Kan inte ta bort kategorin "{category_to_delete.name}" eftersom den innehåller trådar. Flytta eller ta bort trådarna först.', 'danger')
        return redirect(url_for('main.manage_forum_categories'))
    try:
        db.session.delete(category_to_delete); db.session.commit(); flash(f'Kategorin "{category_to_delete.name}" har tagits bort.', 'success')
    except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när kategorin skulle tas bort: {e}', 'danger'); current_app.logger.error(f"Fel vid borttagning av forumkategori {category_id}: {e}")
    return redirect(url_for('main.manage_forum_categories'))


# --- WIKI ROUTES ---
# ...(wiki routes oförändrade)...
@main.route('/wiki')
def wiki_list_pages():
    pages = WikiPage.query.order_by(WikiPage.title).all(); return render_template('wiki/list.html', title="Wiki Index", pages=pages)

@main.route('/wiki/<string:slug>')
def wiki_view_page(slug):
    page = WikiPage.query.filter_by(slug=slug).first_or_404(); html_content = md_converter.convert(page.content)
    return render_template('wiki/view.html', title=page.title, page=page, html_content=Markup(html_content))

@main.route('/wiki/create', methods=['GET', 'POST'])
@login_required
@moderator_required
def wiki_create_page():
    form = WikiPageForm()
    if form.validate_on_submit():
        new_page = WikiPage(title=form.title.data, slug=form.slug.data, content=form.content.data, editor_id=current_user.id)
        try:
            db.session.add(new_page); db.session.flush()
            initial_revision = WikiRevision(page_id=new_page.id, editor_id=current_user.id, timestamp=datetime.datetime.utcnow(), title=new_page.title, content=new_page.content, comment="Initial creation")
            db.session.add(initial_revision); db.session.commit(); flash(f'Wiki-sidan "{new_page.title}" har skapats!', 'success')
            return redirect(url_for('main.wiki_view_page', slug=new_page.slug))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när sidan skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid skapande av wiki-sida: {e}")
    return render_template('wiki/edit_page.html', title="Skapa Ny Wiki-sida", form=form, is_new=True)

@main.route('/wiki/<string:slug>/edit', methods=['GET', 'POST'])
@login_required
@moderator_required
def wiki_edit_page(slug):
    page_to_edit = WikiPage.query.filter_by(slug=slug).first_or_404(); form = WikiPageForm(original_page=page_to_edit)
    if form.validate_on_submit():
        new_revision = WikiRevision(page_id=page_to_edit.id, editor_id=current_user.id, timestamp=datetime.datetime.utcnow(), title=form.title.data, content=form.content.data, comment=form.comment.data)
        page_to_edit.title = form.title.data; page_to_edit.slug = form.slug.data; page_to_edit.content = form.content.data; page_to_edit.editor_id = current_user.id
        try:
            db.session.add(new_revision); db.session.commit(); flash(f'Wiki-sidan "{page_to_edit.title}" har uppdaterats.', 'success')
            return redirect(url_for('main.wiki_view_page', slug=page_to_edit.slug))
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när sidan "{page_to_edit.title}" skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid redigering av wiki-sida {slug}: {e}")
    elif request.method == 'GET': form.title.data = page_to_edit.title; form.slug.data = page_to_edit.slug; form.content.data = page_to_edit.content
    return render_template('wiki/edit_page.html', title=f"Redigera: {page_to_edit.title}", form=form, page=page_to_edit, is_new=False)

@main.route('/wiki/<string:slug>/history')
@login_required
def wiki_page_history(slug):
    page = WikiPage.query.filter_by(slug=slug).first_or_404()
    revisions = page.revisions.order_by(WikiRevision.timestamp.desc()).all()
    return render_template('wiki/history.html', title=f"Historik för {page.title}", page=page, revisions=revisions)

# --- FORUM ROUTES ---
@main.route('/forum')
@login_required
def forum_index():
    categories = ForumCategory.query.order_by(ForumCategory.name).all()
    return render_template('forum/index.html', title="Forum Index", categories=categories)

@main.route('/forum/category/<string:slug>')
@login_required
def view_category(slug):
    category = ForumCategory.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    threads_pagination = ForumThread.query.filter_by(category_id=category.id)\
                               .options(joinedload(ForumThread.author))\
                               .order_by(ForumThread.last_post_at.desc())\
                               .paginate(page=page, per_page=current_app.config['THREADS_PER_PAGE'], error_out=False)
    threads = threads_pagination.items
    return render_template('forum/category.html', title=f"Forum: {category.name}", category=category, threads=threads, pagination=threads_pagination)

@main.route('/forum/thread/<int:thread_id>')
@login_required
def view_thread(thread_id):
    thread = ForumThread.query.options(joinedload(ForumThread.category), joinedload(ForumThread.author)).get_or_404(thread_id)
    page = request.args.get('page', 1, type=int)
    posts_pagination = ForumPost.query.filter_by(thread_id=thread.id)\
                           .options(joinedload(ForumPost.author))\
                           .order_by(ForumPost.created_at.asc())\
                           .paginate(page=page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False)
    posts = posts_pagination.items
    reply_form = PostForm()
    first_post = ForumPost.query.filter_by(thread_id=thread.id).order_by(ForumPost.created_at.asc()).first()
    first_post_id = first_post.id if first_post else None
    rendered_posts = []
    for post in posts:
        post.html_content = Markup(md_converter.convert(post.content))
        rendered_posts.append(post)
    return render_template('forum/thread.html', title=thread.title, thread=thread, posts=rendered_posts, reply_form=reply_form, pagination=posts_pagination, first_post_id=first_post_id)

@main.route('/forum/thread/<int:thread_id>/reply', methods=['POST'])
@login_required
def reply_to_thread(thread_id):
    thread = ForumThread.query.get_or_404(thread_id); form = PostForm()
    if form.validate_on_submit():
        post = ForumPost(content=form.content.data, author_id=current_user.id, thread_id=thread.id)
        thread.last_post_at = datetime.datetime.utcnow()
        try:
            db.session.add(post); db.session.commit(); flash('Ditt svar har publicerats!', 'success')
            count = ForumPost.query.filter_by(thread_id=thread.id).count()
            last_page = (count + current_app.config['POSTS_PER_PAGE'] - 1) // current_app.config['POSTS_PER_PAGE']
            return redirect(url_for('main.view_thread', thread_id=thread.id, page=last_page) + f'#post-{post.id}')
        except Exception as e: db.session.rollback(); flash(f'Kunde inte spara ditt svar: {e}', 'danger'); current_app.logger.error(f"Fel vid svar i tråd {thread_id}: {e}")
        return redirect(url_for('main.view_thread', thread_id=thread.id))
    else: flash('Kunde inte publicera svaret. Kontrollera fältet.', 'danger'); return redirect(url_for('main.view_thread', thread_id=thread.id))

@main.route('/forum/category/<string:slug>/new_thread', methods=['GET', 'POST'])
@login_required
def new_thread(slug):
    category = ForumCategory.query.filter_by(slug=slug).first_or_404(); form = NewThreadForm()
    if form.validate_on_submit():
        thread = ForumThread(title=form.title.data, category_id=category.id, author_id=current_user.id)
        post = ForumPost(content=form.content.data, author_id=current_user.id, thread=thread)
        try:
            db.session.add(thread); db.session.commit(); flash('Ny tråd skapad!', 'success')
            return redirect(url_for('main.view_thread', thread_id=thread.id))
        except Exception as e: db.session.rollback(); flash(f'Kunde inte skapa tråden: {e}', 'danger'); current_app.logger.error(f"Fel vid skapande av tråd i kategori {slug}: {e}")
    return render_template('forum/new_thread.html', title="Skapa Ny Tråd", form=form, category=category)

@main.route('/forum/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post_to_edit = ForumPost.query.options(joinedload(ForumPost.author), joinedload(ForumPost.thread)).get_or_404(post_id)
    if not (post_to_edit.author_id == current_user.id or current_user.is_moderator()):
        flash('Du har inte behörighet att redigera detta inlägg.', 'danger')
        return redirect(url_for('main.view_thread', thread_id=post_to_edit.thread_id))
    form = PostForm()
    if form.validate_on_submit():
        post_to_edit.content = form.content.data
        try:
            db.session.commit(); flash('Inlägget har uppdaterats.', 'success')
            posts_before = ForumPost.query.filter(ForumPost.thread_id == post_to_edit.thread_id, ForumPost.created_at <= post_to_edit.created_at).count()
            page = (posts_before + current_app.config['POSTS_PER_PAGE'] - 1) // current_app.config['POSTS_PER_PAGE']
            return redirect(url_for('main.view_thread', thread_id=post_to_edit.thread_id, page=page) + f'#post-{post_to_edit.id}')
        except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när inlägget skulle sparas: {e}', 'danger'); current_app.logger.error(f"Fel vid redigering av inlägg {post_id}: {e}")
    elif request.method == 'GET': form.content.data = post_to_edit.content
    return render_template('forum/edit_post.html', title="Redigera Inlägg", form=form, post=post_to_edit)

@main.route('/forum/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post_to_delete = ForumPost.query.options(joinedload(ForumPost.thread)).get_or_404(post_id)
    thread_id = post_to_delete.thread_id; thread = post_to_delete.thread
    if not (post_to_delete.author_id == current_user.id or current_user.is_moderator()):
        flash('Du har inte behörighet att ta bort detta inlägg.', 'danger')
        return redirect(url_for('main.view_thread', thread_id=thread_id))
    first_post = ForumPost.query.filter_by(thread_id=thread_id).order_by(ForumPost.created_at.asc()).first()
    if first_post and post_to_delete.id == first_post.id:
        flash('Det första inlägget i en tråd kan inte tas bort här.', 'warning')
        return redirect(url_for('main.view_thread', thread_id=thread_id))
    try:
        db.session.delete(post_to_delete)
        new_last_post = ForumPost.query.filter_by(thread_id=thread_id).order_by(ForumPost.created_at.desc()).first()
        thread.last_post_at = new_last_post.created_at if new_last_post else thread.created_at
        db.session.commit(); flash('Inlägget har tagits bort.', 'success')
    except Exception as e: db.session.rollback(); flash(f'Ett fel uppstod när inlägget skulle tas bort: {e}', 'danger'); current_app.logger.error(f"Fel vid borttagning av inlägg {post_id}: {e}")
    return redirect(url_for('main.view_thread', thread_id=thread_id))

# --- NY ROUTE FÖR ATT TA BORT FORUMTRÅDAR (MODERATOR) ---
@main.route('/forum/thread/<int:thread_id>/delete', methods=['POST'])
@login_required
@moderator_required # Endast moderatorer får ta bort hela trådar
def delete_thread(thread_id):
    """ Tar bort en hel forumtråd och alla dess inlägg. """
    thread_to_delete = ForumThread.query.options(joinedload(ForumThread.category)).get_or_404(thread_id)
    category_slug = thread_to_delete.category.slug # Spara slug för redirect

    try:
        # Tack vare cascade='all, delete-orphan' på thread.posts raderas alla inlägg automatiskt
        db.session.delete(thread_to_delete)
        db.session.commit()
        flash(f'Tråden "{thread_to_delete.title}" och alla dess inlägg har tagits bort.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ett fel uppstod när tråden skulle tas bort: {e}', 'danger')
        current_app.logger.error(f"Fel vid borttagning av tråd {thread_id}: {e}")
        # Omdirigera tillbaka till tråden om borttagning misslyckas
        return redirect(url_for('main.view_thread', thread_id=thread_id))

    # Omdirigera till kategorin tråden låg i
    return redirect(url_for('main.view_category', slug=category_slug))
# --- SLUT NY ROUTE ---


# --- Placeholder för Server Status API ---
@main.route("/api/server-status")
def server_status_api():
    try: return {"server_name": "Team Core Game Server", "status": "offline", "players": 0, "max_players": 20}
    except Exception as e: current_app.logger.error(f"Kunde inte hämta serverstatus: {e}"); return {"server_name": "Team Core Game Server", "status": "error", "players": "?", "max_players": "?"}, 500