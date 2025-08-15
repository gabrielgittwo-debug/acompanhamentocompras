from datetime import datetime
from enum import Enum
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# User roles enum
class UserRole(Enum):
    ADMIN = 'admin'
    SOLICITANTE = 'solicitante'
    APROVADOR = 'aprovador'
    RECEBIMENTO = 'recebimento'

# Acquisition types enum
class AcquisitionType(Enum):
    SERVICO = 'servico'
    INSUMO = 'insumo'

# Status enum
class AcquisitionStatus(Enum):
    EM_ANALISE = 'em_analise'
    APROVADO = 'aprovado'
    EM_COTACAO = 'em_cotacao'
    PEDIDO_REALIZADO = 'pedido_realizado'
    RECEBIDO = 'recebido'
    FECHADO = 'fechado'

# Payment methods enum
class PaymentMethod(Enum):
    DINHEIRO = 'dinheiro'
    CARTAO_CREDITO = 'cartao_credito'
    CARTAO_DEBITO = 'cartao_debito'
    TRANSFERENCIA = 'transferencia'
    BOLETO = 'boleto'
    PIX = 'pix'

# Budget sources enum
class BudgetSource(Enum):
    VERBA_ESTADUAL = 'verba_estadual'
    RECURSO_PROPRIO = 'recurso_proprio'
    FEDERAL = 'federal'
    OUTROS = 'outros'

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    role = db.Column(db.Enum(UserRole), default=UserRole.SOLICITANTE)
    active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    acquisitions = db.relationship('Acquisition', foreign_keys='Acquisition.requester_id', backref='requester')
    approvals = db.relationship('Acquisition', foreign_keys='Acquisition.approver_id', backref='approver')
    status_changes = db.relationship('StatusHistory', backref='user')

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email or "Usuário"

    def can_approve(self):
        return self.role in [UserRole.ADMIN, UserRole.APROVADOR]

    def can_receive(self):
        return self.role in [UserRole.ADMIN, UserRole.RECEBIMENTO]

    def is_admin(self):
        return self.role == UserRole.ADMIN

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class CostCenter(db.Model):
    __tablename__ = 'cost_centers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    acquisitions = db.relationship('Acquisition', backref='cost_center')

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(AcquisitionType), nullable=False)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    acquisitions = db.relationship('Acquisition', backref='category')

class Acquisition(db.Model):
    __tablename__ = 'acquisitions'
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic info
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(AcquisitionType), nullable=False)
    quantity = db.Column(db.Integer)
    unit = db.Column(db.String(50))
    
    # Status and workflow
    status = db.Column(db.Enum(AcquisitionStatus), default=AcquisitionStatus.EM_ANALISE)
    justification = db.Column(db.Text, nullable=False)
    
    # Financial info
    estimated_value = db.Column(db.Numeric(12, 2))
    final_value = db.Column(db.Numeric(12, 2))
    payment_method = db.Column(db.Enum(PaymentMethod))
    budget_source = db.Column(db.Enum(BudgetSource))
    
    # Relationships
    requester_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    approver_id = db.Column(db.String, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    approved_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    status_history = db.relationship('StatusHistory', backref='acquisition', order_by='StatusHistory.created_at')
    documents = db.relationship('Document', backref='acquisition')

    @property
    def status_display(self):
        status_map = {
            AcquisitionStatus.EM_ANALISE: 'Em Análise',
            AcquisitionStatus.APROVADO: 'Aprovado',
            AcquisitionStatus.EM_COTACAO: 'Em Cotação',
            AcquisitionStatus.PEDIDO_REALIZADO: 'Pedido Realizado',
            AcquisitionStatus.RECEBIDO: 'Recebido/Concluído',
            AcquisitionStatus.FECHADO: 'Fechado'
        }
        return status_map.get(self.status, self.status.value)

    @property
    def type_display(self):
        return 'Serviço' if self.type == AcquisitionType.SERVICO else 'Insumo'

    @property
    def days_since_creation(self):
        return (datetime.now() - self.created_at).days

class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    id = db.Column(db.Integer, primary_key=True)
    
    acquisition_id = db.Column(db.Integer, db.ForeignKey('acquisitions.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    
    old_status = db.Column(db.Enum(AcquisitionStatus))
    new_status = db.Column(db.Enum(AcquisitionStatus), nullable=False)
    comment = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    
    acquisition_id = db.Column(db.Integer, db.ForeignKey('acquisitions.id'), nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    uploaded_by = db.relationship('User', backref='uploaded_documents')
