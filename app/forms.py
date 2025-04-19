# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
# Importera ForumCategory nu också
from app.models import User, Role, WikiPage, ForumCategory
from app import db
import re

# Funktion för att hämta roller
def role_query_factory():
    return Role.query.order_by(Role.name)
# Funktion för att få etikett för roller
def get_role_label(role):
    return role.name.capitalize()

# -- Registreringsformulär --
class RegistrationForm(FlaskForm):
    username = StringField('Användarnamn', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('E-post', validators=[DataRequired(), Email()])
    password = PasswordField('Lösenord', validators=[DataRequired()])
    confirm_password = PasswordField('Bekräfta Lösenord', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrera')
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user: raise ValidationError('Det användarnamnet är upptaget.')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user: raise ValidationError('Den e-postadressen används redan.')

# -- Inloggningsformulär --
class LoginForm(FlaskForm):
    email = StringField('E-post', validators=[DataRequired(), Email()])
    password = PasswordField('Lösenord', validators=[DataRequired()])
    remember = BooleanField('Kom ihåg mig')
    submit = SubmitField('Logga In')

# -- Supportformulär --
class SupportForm(FlaskForm):
    email = StringField('Din E-postadress', validators=[DataRequired(), Email()])
    subject = StringField('Ämne', validators=[DataRequired(), Length(min=5, max=100)])
    message = TextAreaField('Meddelande', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Skicka Supportärende')
    def __init__(self, *args, **kwargs):
        super(SupportForm, self).__init__(*args, **kwargs)
        from flask_login import current_user
        if current_user.is_authenticated and not self.email.data:
            self.email.data = current_user.email

# -- Formulär för att redigera användare --
class EditUserForm(FlaskForm):
    username = StringField('Användarnamn', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('E-post', validators=[DataRequired(), Email()])
    role = QuerySelectField('Användarroll', query_factory=role_query_factory, get_label=get_role_label, allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Spara ändringar')
    def __init__(self, original_user, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_user = original_user
    def validate_username(self, username):
        if username.data != self.original_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user: raise ValidationError('Det användarnamnet är upptaget.')
    def validate_email(self, email):
        if email.data != self.original_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user: raise ValidationError('Den e-postadressen används redan.')

# -- Formulär för att skapa användare (Admin) --
class AdminCreateUserForm(FlaskForm):
    username = StringField('Användarnamn', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('E-post', validators=[DataRequired(), Email()])
    password = PasswordField('Lösenord', validators=[DataRequired()])
    confirm_password = PasswordField('Bekräfta Lösenord', validators=[DataRequired(), EqualTo('password')])
    role = QuerySelectField('Användarroll', query_factory=role_query_factory, get_label=get_role_label, allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Skapa Användare')
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user: raise ValidationError('Det användarnamnet är upptaget.')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user: raise ValidationError('Den e-postadressen används redan.')

# -- Formulär för att skapa/redigera Roller --
class RoleForm(FlaskForm):
    name = StringField('Rollnamn', validators=[DataRequired(), Length(max=64)])
    description = StringField('Beskrivning (valfri)', validators=[Length(max=255)])
    submit = SubmitField('Spara Roll')
    def __init__(self, original_role=None, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.original_role = original_role
    def validate_name(self, name_field):
        # Använd ilike för case-insensitive jämförelse
        name_to_check = name_field.data.capitalize() # Jämför med kapitaliserad version? Eller spara som det är?
        if self.original_role is None or name_to_check != self.original_role.name:
            role = Role.query.filter(Role.name.ilike(name_to_check)).first()
            if role: raise ValidationError('Det rollnamnet finns redan.')

# -- Formulär för Wiki-sidor --
class WikiPageForm(FlaskForm):
    title = StringField('Titel', validators=[DataRequired(), Length(max=100)])
    slug = StringField('URL Slug (t.ex. "min-forsta-sida")', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Innehåll (Markdown)', validators=[DataRequired()])
    comment = StringField('Ändringskommentar (valfri)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Spara Sida')
    def __init__(self, original_page=None, *args, **kwargs):
        super(WikiPageForm, self).__init__(*args, **kwargs)
        self.original_page = original_page
    def validate_slug(self, slug_field):
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', slug_field.data): raise ValidationError('Slug får endast innehålla små bokstäver, siffror och bindestreck.')
        if self.original_page is None or slug_field.data != self.original_page.slug:
            page = WikiPage.query.filter_by(slug=slug_field.data).first()
            if page: raise ValidationError('Denna URL slug används redan.')

# -- Formulär för Forum-inlägg (Svar) --
class PostForm(FlaskForm):
    content = TextAreaField('Ditt svar (Markdown)', validators=[DataRequired()])
    submit = SubmitField('Skicka Svar')

# -- Formulär för Ny Forum-tråd --
class NewThreadForm(FlaskForm):
    title = StringField('Trådtitel', validators=[DataRequired(), Length(min=5, max=150)])
    content = TextAreaField('Första inlägget (Markdown)', validators=[DataRequired()])
    submit = SubmitField('Skapa Tråd')

# --- NYTT FORMULÄR FÖR FORUMKATEGORIER ---
class ForumCategoryForm(FlaskForm):
    name = StringField('Kategorinamn', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beskrivning (valfri)')
    submit = SubmitField('Spara Kategori')

    # Init för att hantera redigering (validera unikt namn)
    def __init__(self, original_category=None, *args, **kwargs):
        super(ForumCategoryForm, self).__init__(*args, **kwargs)
        self.original_category = original_category

    # Anpassad validering för kategorinamn
    def validate_name(self, name_field):
        # Kontrollera bara om namnet ändrats eller om det är en ny kategori
        if self.original_category is None or name_field.data != self.original_category.name:
            # Använd ilike för case-insensitive sökning
            category = ForumCategory.query.filter(ForumCategory.name.ilike(name_field.data)).first()
            if category:
                raise ValidationError('Det kategorinamnet finns redan. Välj ett annat.')