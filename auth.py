"""
Simple Flask-Login authentication system for SENAI Acquisition Management
Replaces Replit Auth with email/password authentication
"""

import os
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash

from app import app, db
from models import User, PendingUser, UserRole

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    return User.query.get(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access"""
    return redirect(url_for('auth.login'))

from flask import Blueprint

# Create auth blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.approved:
                flash('Sua conta ainda não foi aprovada pelo administrador.', 'warning')
                return render_template('auth/login.html')
            
            if not user.active:
                flash('Sua conta foi desativada. Entre em contato com o administrador.', 'error')
                return render_template('auth/login.html')
            
            # Login successful
            login_user(user, remember=remember)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').lower().strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        requested_role = request.form.get('requested_role', 'solicitante')
        message = request.form.get('message', '').strip()
        
        # Validation
        errors = []
        if not email:
            errors.append('Email é obrigatório.')
        if not first_name:
            errors.append('Nome é obrigatório.')
        if not last_name:
            errors.append('Sobrenome é obrigatório.')
        if not password:
            errors.append('Senha é obrigatória.')
        if len(password) < 6:
            errors.append('Senha deve ter pelo menos 6 caracteres.')
        if password != password_confirm:
            errors.append('Senhas não conferem.')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('Email já cadastrado.')
        if PendingUser.query.filter_by(email=email).first():
            errors.append('Já existe uma solicitação pendente para este email.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', UserRole=UserRole)
        
        try:
            # Create pending user
            pending_user = PendingUser(
                email=email,
                first_name=first_name,
                last_name=last_name,
                requested_role=UserRole(requested_role),
                message=message
            )
            pending_user.set_password(password)
            
            db.session.add(pending_user)
            db.session.commit()
            
            flash('Solicitação de cadastro enviada! Aguarde aprovação do administrador.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar solicitação: {str(e)}', 'error')
    
    return render_template('auth/register.html', UserRole=UserRole)

@auth_bp.route('/logout')
def logout():
    """Logout"""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('index'))

# Admin routes for user management
@auth_bp.route('/admin/pending-users')
@login_required
def admin_pending_users():
    """View pending user registrations (admin only)"""
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    pending_users = PendingUser.query.order_by(PendingUser.created_at.desc()).all()
    return render_template('auth/admin_pending.html', pending_users=pending_users, UserRole=UserRole)

@auth_bp.route('/admin/approve-user/<int:pending_id>', methods=['POST'])
@login_required
def approve_user(pending_id):
    """Approve pending user registration"""
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    pending_user = PendingUser.query.get_or_404(pending_id)
    approved_role = UserRole(request.form.get('approved_role', pending_user.requested_role.value))
    
    try:
        # Create approved user
        user = User(
            email=pending_user.email,
            first_name=pending_user.first_name,
            last_name=pending_user.last_name,
            password_hash=pending_user.password_hash,
            role=approved_role,
            approved=True,
            approved_by_id=current_user.id,
            approved_at=db.func.now()
        )
        
        db.session.add(user)
        db.session.delete(pending_user)
        db.session.commit()
        
        flash(f'Usuário {user.full_name} aprovado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao aprovar usuário: {str(e)}', 'error')
    
    return redirect(url_for('auth.admin_pending_users'))

@auth_bp.route('/admin/reject-user/<int:pending_id>', methods=['POST'])
@login_required
def reject_user(pending_id):
    """Reject pending user registration"""
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    pending_user = PendingUser.query.get_or_404(pending_id)
    
    try:
        db.session.delete(pending_user)
        db.session.commit()
        flash(f'Solicitação de {pending_user.full_name} rejeitada.', 'info')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao rejeitar usuário: {str(e)}', 'error')
    
    return redirect(url_for('auth.admin_pending_users'))

# Initialize admin user if needed
def create_admin_user():
    """Create the default admin user gabriel@suporte.com / 4731v8"""
    admin_email = 'gabriel@suporte.com'
    
    # Check if admin already exists
    admin = User.query.filter_by(email=admin_email).first()
    if admin:
        return
    
    try:
        # Create admin user
        admin = User(
            email=admin_email,
            first_name='Gabriel',
            last_name='Administrador',
            role=UserRole.ADMIN,
            approved=True,
            active=True
        )
        admin.set_password('4731v8')
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user created: {admin_email} / 4731v8")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {e}")

# Register blueprint
app.register_blueprint(auth_bp)