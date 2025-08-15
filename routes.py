import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_login import current_user, login_required
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload

from app import app, db
from models import (User, Acquisition, Category, CostCenter, StatusHistory, Document, 
                   AcquisitionType, AcquisitionStatus, UserRole, PaymentMethod, BudgetSource)
from utils.pdf_generator import generate_report_pdf
from utils.excel_generator import generate_excel_report
from utils.excel_importer import import_excel_acquisitions, parse_excel_preview

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get statistics for dashboard
    total_acquisitions = Acquisition.query.count()
    servicos_count = Acquisition.query.filter_by(type=AcquisitionType.SERVICO).count()
    insumos_count = Acquisition.query.filter_by(type=AcquisitionType.INSUMO).count()
    
    pending_approvals = Acquisition.query.filter_by(status=AcquisitionStatus.EM_ANALISE).count()
    
    # Recent acquisitions
    recent_acquisitions = Acquisition.query.options(
        joinedload(Acquisition.category),
        joinedload(Acquisition.requester)
    ).order_by(Acquisition.created_at.desc()).limit(5).all()
    
    # Monthly spending data for chart
    current_year = datetime.now().year
    monthly_data = db.session.query(
        func.extract('month', Acquisition.created_at).label('month'),
        Acquisition.type,
        func.sum(Acquisition.final_value).label('total')
    ).filter(
        func.extract('year', Acquisition.created_at) == current_year,
        Acquisition.final_value.isnot(None)
    ).group_by(
        func.extract('month', Acquisition.created_at),
        Acquisition.type
    ).all()
    
    # Status distribution
    status_data = db.session.query(
        Acquisition.status,
        func.count(Acquisition.id).label('count')
    ).group_by(Acquisition.status).all()
    
    return render_template('dashboard.html',
                         total_acquisitions=total_acquisitions,
                         servicos_count=servicos_count,
                         insumos_count=insumos_count,
                         pending_approvals=pending_approvals,
                         recent_acquisitions=recent_acquisitions,
                         monthly_data=monthly_data,
                         status_data=status_data)

@app.route('/acquisitions/new')
@login_required
def new_acquisition():
    categories = Category.query.filter_by(active=True).all()
    cost_centers = CostCenter.query.filter_by(active=True).all()
    
    # Convert to JSON-serializable format
    categories_json = [{'id': c.id, 'name': c.name, 'type': c.type.value} for c in categories]
    cost_centers_json = [{'id': c.id, 'name': c.name, 'code': c.code} for c in cost_centers]
    
    return render_template('acquisition/new.html', 
                         categories=categories, 
                         cost_centers=cost_centers,
                         categories_json=categories_json,
                         cost_centers_json=cost_centers_json,
                         AcquisitionType=AcquisitionType,
                         BudgetSource=BudgetSource)

@app.route('/acquisitions/create', methods=['POST'])
@login_required
def create_acquisition():
    try:
        acquisition = Acquisition()
        acquisition.title = request.form['title']
        acquisition.description = request.form['description']
        acquisition.type = AcquisitionType(request.form['type'])
        acquisition.quantity = int(request.form.get('quantity')) if request.form.get('quantity') else None
        acquisition.unit = request.form.get('unit')
        acquisition.justification = request.form['justification']
        acquisition.estimated_value = float(request.form.get('estimated_value')) if request.form.get('estimated_value') else None
        acquisition.budget_source = BudgetSource(request.form['budget_source'])
        acquisition.category_id = int(request.form['category_id'])
        acquisition.cost_center_id = int(request.form['cost_center_id'])
        acquisition.requester_id = current_user.id
        
        db.session.add(acquisition)
        db.session.flush()
        
        # Create initial status history
        status_history = StatusHistory()
        status_history.acquisition_id = acquisition.id
        status_history.user_id = current_user.id
        status_history.new_status = AcquisitionStatus.EM_ANALISE
        status_history.comment = "Solicitação criada"
        db.session.add(status_history)
        db.session.commit()
        
        flash('Solicitação criada com sucesso!', 'success')
        return redirect(url_for('acquisition_detail', id=acquisition.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar solicitação: {str(e)}', 'error')
        return redirect(url_for('new_acquisition'))

@app.route('/acquisitions')
@login_required
def list_acquisitions():
    page = request.args.get('page', 1, type=int)
    type_filter = request.args.get('type')
    status_filter = request.args.get('status')
    category_filter = request.args.get('category_id', type=int)
    
    query = Acquisition.query.options(
        joinedload(Acquisition.category),
        joinedload(Acquisition.cost_center),
        joinedload(Acquisition.requester)
    )
    
    # Apply filters
    if type_filter:
        query = query.filter(Acquisition.type == AcquisitionType(type_filter))
    if status_filter:
        query = query.filter(Acquisition.status == AcquisitionStatus(status_filter))
    if category_filter:
        query = query.filter(Acquisition.category_id == category_filter)
    
    # Role-based filtering
    if not current_user.is_admin():
        if current_user.role == UserRole.SOLICITANTE:
            query = query.filter(Acquisition.requester_id == current_user.id)
    
    acquisitions = query.order_by(Acquisition.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.filter_by(active=True).all()
    
    return render_template('acquisition/list.html',
                         acquisitions=acquisitions,
                         categories=categories,
                         AcquisitionType=AcquisitionType,
                         AcquisitionStatus=AcquisitionStatus,
                         type_filter=type_filter,
                         status_filter=status_filter,
                         category_filter=category_filter)

@app.route('/acquisitions/<int:id>')
@login_required
def acquisition_detail(id):
    acquisition = Acquisition.query.options(
        joinedload(Acquisition.category),
        joinedload(Acquisition.cost_center),
        joinedload(Acquisition.requester),
        joinedload(Acquisition.approver),
        joinedload(Acquisition.status_history),
        joinedload(Acquisition.documents)
    ).get_or_404(id)
    
    # Check access permissions
    if not current_user.is_admin() and current_user.role == UserRole.SOLICITANTE:
        if acquisition.requester_id != current_user.id:
            flash('Acesso negado.', 'error')
            return redirect(url_for('list_acquisitions'))
    
    return render_template('acquisition/detail.html',
                         acquisition=acquisition,
                         PaymentMethod=PaymentMethod,
                         AcquisitionStatus=AcquisitionStatus,
                         now=datetime.now,
                         timedelta=timedelta)

@app.route('/acquisitions/<int:id>/update-status', methods=['POST'])
@login_required
def update_acquisition_status(id):
    acquisition = Acquisition.query.get_or_404(id)
    new_status = AcquisitionStatus(request.form['status'])
    comment = request.form.get('comment', '')
    
    # Check permissions
    can_update = False
    if current_user.is_admin():
        can_update = True
    elif new_status == AcquisitionStatus.APROVADO and current_user.can_approve():
        can_update = True
    elif new_status == AcquisitionStatus.RECEBIDO and current_user.can_receive():
        can_update = True
    
    if not can_update:
        flash('Você não tem permissão para alterar este status.', 'error')
        return redirect(url_for('acquisition_detail', id=id))
    
    try:
        old_status = acquisition.status
        acquisition.status = new_status
        
        # Update specific timestamps and fields
        if new_status == AcquisitionStatus.APROVADO:
            acquisition.approved_at = datetime.now()
            acquisition.approver_id = current_user.id
        elif new_status == AcquisitionStatus.AGUARDANDO_ORCAMENTO:
            acquisition.budget_requested_at = datetime.now()
            if request.form.get('budget_deadline'):
                acquisition.budget_deadline = datetime.strptime(request.form['budget_deadline'], '%Y-%m-%d')
        elif new_status == AcquisitionStatus.ORCAMENTO_RECEBIDO:
            acquisition.budget_received_at = datetime.now()
            if request.form.get('budget_value'):
                acquisition.budget_value = float(request.form['budget_value'])
            if request.form.get('budget_provider'):
                acquisition.budget_provider = request.form['budget_provider']
            if request.form.get('budget_notes'):
                acquisition.budget_notes = request.form['budget_notes']
        elif new_status == AcquisitionStatus.RECEBIDO:
            acquisition.completed_at = datetime.now()
        
        # Update financial info if provided
        if request.form.get('final_value'):
            acquisition.final_value = float(request.form['final_value'])
        if request.form.get('payment_method'):
            acquisition.payment_method = PaymentMethod(request.form['payment_method'])
        
        # Create status history entry
        status_history = StatusHistory()
        status_history.acquisition_id = acquisition.id
        status_history.user_id = current_user.id
        status_history.old_status = old_status
        status_history.new_status = new_status
        status_history.comment = comment
        
        db.session.add(status_history)
        db.session.commit()
        
        flash('Status atualizado com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar status: {str(e)}', 'error')
    
    return redirect(url_for('acquisition_detail', id=id))

@app.route('/acquisitions/<int:id>/upload-document', methods=['POST'])
@login_required
def upload_document(id):
    acquisition = Acquisition.query.get_or_404(id)
    
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('acquisition_detail', id=id))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('acquisition_detail', id=id))
    
    if file:
        try:
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(app.root_path, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate secure filename
            original_filename = file.filename
            filename = secure_filename(f"{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}")
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            file.save(file_path)
            
            # Create document record
            document = Document()
            document.acquisition_id = id
            document.user_id = current_user.id
            document.filename = filename
            document.original_filename = original_filename
            document.file_path = file_path
            document.file_size = os.path.getsize(file_path)
            document.mime_type = file.mimetype
            document.description = request.form.get('description', '')
            
            db.session.add(document)
            db.session.commit()
            
            flash('Documento enviado com sucesso!', 'success')
            
        except Exception as e:
            flash(f'Erro ao enviar documento: {str(e)}', 'error')
    
    return redirect(url_for('acquisition_detail', id=id))

@app.route('/reports')
@login_required
def reports():
    # Summary statistics
    total_value = db.session.query(func.sum(Acquisition.final_value)).scalar() or 0
    servicos_value = db.session.query(func.sum(Acquisition.final_value)).filter(
        Acquisition.type == AcquisitionType.SERVICO
    ).scalar() or 0
    insumos_value = db.session.query(func.sum(Acquisition.final_value)).filter(
        Acquisition.type == AcquisitionType.INSUMO
    ).scalar() or 0
    
    # Monthly data for current year
    current_year = datetime.now().year
    monthly_data = db.session.query(
        func.extract('month', Acquisition.created_at).label('month'),
        Acquisition.type,
        func.sum(Acquisition.final_value).label('total'),
        func.count(Acquisition.id).label('count')
    ).filter(
        func.extract('year', Acquisition.created_at) == current_year,
        Acquisition.final_value.isnot(None)
    ).group_by(
        func.extract('month', Acquisition.created_at),
        Acquisition.type
    ).all()
    
    # Cost center breakdown
    cost_center_data = db.session.query(
        CostCenter.name,
        func.sum(Acquisition.final_value).label('total'),
        func.count(Acquisition.id).label('count')
    ).join(Acquisition).filter(
        Acquisition.final_value.isnot(None)
    ).group_by(CostCenter.name).all()
    
    return render_template('reports/index.html',
                         total_value=total_value,
                         servicos_value=servicos_value,
                         insumos_value=insumos_value,
                         monthly_data=monthly_data,
                         cost_center_data=cost_center_data)

@app.route('/reports/export-pdf')
@login_required
def export_pdf_report():
    try:
        # Get filtered data
        acquisitions = Acquisition.query.options(
            joinedload(Acquisition.category),
            joinedload(Acquisition.cost_center),
            joinedload(Acquisition.requester)
        ).all()
        
        pdf_file = generate_report_pdf(acquisitions)
        return send_file(pdf_file, as_attachment=True, download_name='relatorio_aquisicoes.pdf')
        
    except Exception as e:
        flash(f'Erro ao gerar relatório PDF: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/reports/export-excel')
@login_required
def export_excel_report():
    try:
        # Get filtered data
        acquisitions = Acquisition.query.options(
            joinedload(Acquisition.category),
            joinedload(Acquisition.cost_center),
            joinedload(Acquisition.requester)
        ).all()
        
        excel_file = generate_excel_report(acquisitions)
        return send_file(excel_file, as_attachment=True, download_name='relatorio_aquisicoes.xlsx')
        
    except Exception as e:
        flash(f'Erro ao gerar relatório Excel: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users, UserRole=UserRole)

@app.route('/admin/users/<string:user_id>/update-role', methods=['POST'])
@login_required
def update_user_role(user_id):
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    new_role = UserRole(request.form['role'])
    
    try:
        user.role = new_role
        db.session.commit()
        flash(f'Perfil do usuário {user.full_name} atualizado para {new_role.value}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar perfil: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/panel')
@login_required
def admin_panel():
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('admin/panel.html')

# Initialize default data
def create_default_data():
    # Create default categories
    if Category.query.count() == 0:
        # Service categories
        service_categories = [
            ('Manutenção Predial', 'Pintura, elétrica, hidráulica, reformas, carpintaria'),
            ('Serviços de Limpeza', 'Limpeza predial, jardinagem e portaria'),
            ('Consultoria/Treinamento', 'Consultorias técnicas ou treinamentos externos'),
            ('Instalação/Configuração', 'Instalação ou configuração de sistemas e equipamentos'),
            ('Mão de Obra Temporária', 'Contratos temporários de mão de obra especializada'),
            ('Serviços de Segurança', 'Vigilância, monitoramento e segurança patrimonial'),
            ('Transporte e Logística', 'Fretes, mudanças e transporte de equipamentos'),
            ('Serviços Gráficos', 'Impressão, encadernação e materiais promocionais'),
            ('Calibração e Manutenção', 'Calibração de equipamentos e manutenção preventiva'),
            ('Serviços de Comunicação', 'Telefonia, internet e sistemas de comunicação')
        ]
        
        for name, desc in service_categories:
            category = Category()
            category.name = name
            category.description = desc
            category.type = AcquisitionType.SERVICO
            db.session.add(category)
        
        # Supply categories
        supply_categories = [
            ('Equipamentos de Laboratório', 'Multímetros, osciloscópios, bancadas, ferramentas de precisão'),
            ('Equipamentos de Informática', 'Computadores, notebooks, periféricos, redes'),
            ('Equipamentos de Cursos', 'Equipamentos para desenvolvimento, logística, mecânica, eletrotécnica'),
            ('Materiais de Consumo', 'Papel, tinta, cabos, componentes eletrônicos, peças de reposição'),
            ('Software/Licenças', 'Software educacional, sistemas operacionais, licenças'),
            ('Mobiliário Escolar', 'Carteiras, cadeiras, mesas, armários, quadros'),
            ('Equipamentos de Segurança', 'EPIs, extintores, câmeras, alarmes'),
            ('Material Didático', 'Livros, apostilas, materiais pedagógicos'),
            ('Ferramentas e Instrumentos', 'Ferramentas manuais, instrumentos de medição'),
            ('Materiais de Construção', 'Materiais para obras e reformas prediais'),
            ('Equipamentos Audiovisuais', 'Projetores, telas, sistemas de som, TVs'),
            ('Materiais de Escritório', 'Papelaria, suprimentos administrativos')
        ]
        
        for name, desc in supply_categories:
            category = Category()
            category.name = name
            category.description = desc
            category.type = AcquisitionType.INSUMO
            db.session.add(category)
    
    # Create default cost centers
    if CostCenter.query.count() == 0:
        cost_centers = [
            ('ADM', 'Administração', 'Centro de custo administrativo'),
            ('LAB', 'Laboratórios', 'Laboratórios e oficinas'),
            ('INFO', 'Informática', 'Tecnologia da informação'),
            ('MAN', 'Manutenção', 'Manutenção predial'),
            ('CURSO', 'Cursos', 'Cursos técnicos e profissionalizantes')
        ]
        
        for code, name, desc in cost_centers:
            cost_center = CostCenter()
            cost_center.code = code
            cost_center.name = name
            cost_center.description = desc
            db.session.add(cost_center)
    
    db.session.commit()

# Excel Import Routes
@app.route('/admin/import-excel')
@login_required
def import_excel_page():
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('admin/import_excel.html')

@app.route('/admin/import-excel/upload', methods=['POST'])
@login_required
def upload_excel_import():
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('import_excel_page'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('import_excel_page'))
    
    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            # Save temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                file.save(tmp_file.name)
                
                # Preview the file
                preview_result = parse_excel_preview(tmp_file.name)
                
                if preview_result['success']:
                    # Store file path in session for import
                    session['import_file_path'] = tmp_file.name
                    
                    return render_template('admin/import_preview.html', 
                                         preview=preview_result['preview'],
                                         total_rows=preview_result['total_rows'])
                else:
                    flash(f'Erro ao processar arquivo: {preview_result["error"]}', 'error')
                    
        except Exception as e:
            flash(f'Erro ao processar arquivo: {str(e)}', 'error')
    else:
        flash('Arquivo deve ser .xlsx ou .xls', 'error')
    
    return redirect(url_for('import_excel_page'))

@app.route('/admin/import-excel/confirm', methods=['POST'])
@login_required
def confirm_excel_import():
    if not current_user.is_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    
    file_path = session.get('import_file_path')
    if not file_path:
        flash('Arquivo não encontrado. Tente novamente.', 'error')
        return redirect(url_for('import_excel_page'))
    
    try:
        result = import_excel_acquisitions(file_path, current_user.id)
        
        if result['success']:
            flash(f'Importação concluída! {result["imported_count"]} aquisições importadas.', 'success')
            if result['errors']:
                flash(f'Alguns erros ocorreram: {", ".join(result["errors"][:3])}', 'warning')
        else:
            flash(f'Erro na importação: {result["error"]}', 'error')
            
        # Clean up
        import os
        if os.path.exists(file_path):
            os.unlink(file_path)
        session.pop('import_file_path', None)
        
    except Exception as e:
        flash(f'Erro na importação: {str(e)}', 'error')
    
    return redirect(url_for('list_acquisitions'))

# Budget management routes
@app.route('/acquisitions/<int:id>/budget', methods=['POST'])
@login_required
def update_budget(id):
    acquisition = Acquisition.query.get_or_404(id)
    
    # Check permissions (admin or requester can update budget info)
    if not (current_user.is_admin() or acquisition.requester_id == current_user.id):
        flash('Você não tem permissão para alterar estas informações.', 'error')
        return redirect(url_for('acquisition_detail', id=id))
    
    try:
        action = request.form.get('action')
        
        if action == 'request_budget':
            acquisition.status = AcquisitionStatus.AGUARDANDO_ORCAMENTO
            acquisition.budget_requested_at = datetime.now()
            if request.form.get('budget_deadline'):
                acquisition.budget_deadline = datetime.strptime(request.form['budget_deadline'], '%Y-%m-%d')
            
            # Create status history
            status_history = StatusHistory()
            status_history.acquisition_id = acquisition.id
            status_history.user_id = current_user.id
            status_history.old_status = acquisition.status
            status_history.new_status = AcquisitionStatus.AGUARDANDO_ORCAMENTO
            status_history.comment = f"Orçamento solicitado - Prazo: {request.form.get('budget_deadline', 'Não definido')}"
            db.session.add(status_history)
            
        elif action == 'receive_budget':
            acquisition.status = AcquisitionStatus.ORCAMENTO_RECEBIDO
            acquisition.budget_received_at = datetime.now()
            
            if request.form.get('budget_value'):
                acquisition.budget_value = float(request.form['budget_value'])
            if request.form.get('budget_provider'):
                acquisition.budget_provider = request.form['budget_provider']
            if request.form.get('budget_notes'):
                acquisition.budget_notes = request.form['budget_notes']
            
            # Create status history
            status_history = StatusHistory()
            status_history.acquisition_id = acquisition.id
            status_history.user_id = current_user.id
            status_history.old_status = acquisition.status
            status_history.new_status = AcquisitionStatus.ORCAMENTO_RECEBIDO
            status_history.comment = f"Orçamento recebido - Valor: R$ {acquisition.budget_value} - Fornecedor: {acquisition.budget_provider}"
            db.session.add(status_history)
        
        db.session.commit()
        flash('Informações do orçamento atualizadas com sucesso!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar orçamento: {str(e)}', 'error')
    
    return redirect(url_for('acquisition_detail', id=id))
