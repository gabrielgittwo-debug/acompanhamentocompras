import pandas as pd
from datetime import datetime
from app import db
from models import Acquisition, Category, CostCenter, AcquisitionType, AcquisitionStatus, User

def import_excel_acquisitions(file_path, user_id):
    """Import acquisitions from Excel file"""
    try:
        # Read Excel with correct header row (row 2, 0-indexed)
        df = pd.read_excel(file_path, header=2)
        
        # Clean column names
        df.columns = ['numero', 'descricao', 'responsavel_cotacao', 'status']
        
        # Remove empty rows
        df = df.dropna(subset=['numero', 'descricao'])
        
        # Get or create default category and cost center
        default_category = Category.query.filter_by(name='Geral').first()
        if not default_category:
            default_category = Category(
                name='Geral',
                type=AcquisitionType.INSUMO,
                description='Categoria padrão para importação'
            )
            db.session.add(default_category)
            db.session.flush()
        
        default_cost_center = CostCenter.query.filter_by(name='Geral').first()
        if not default_cost_center:
            default_cost_center = CostCenter(
                name='Geral',
                code='GERAL',
                description='Centro de custo padrão'
            )
            db.session.add(default_cost_center)
            db.session.flush()
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Map status from Excel to system status
                excel_status = str(row['status']).lower() if pd.notna(row['status']) else 'não iniciada'
                
                if 'não iniciada' in excel_status:
                    system_status = AcquisitionStatus.EM_ANALISE
                elif 'iniciada' in excel_status or 'andamento' in excel_status:
                    system_status = AcquisitionStatus.EM_COTACAO
                elif 'concluída' in excel_status or 'finalizada' in excel_status:
                    system_status = AcquisitionStatus.RECEBIDO
                else:
                    system_status = AcquisitionStatus.EM_ANALISE
                
                # Check if acquisition already exists
                existing = Acquisition.query.filter_by(
                    title=str(row['descricao'])[:200]
                ).first()
                
                if existing:
                    continue  # Skip duplicates
                
                # Create new acquisition
                acquisition = Acquisition(
                    title=str(row['descricao'])[:200],
                    description=f"Importado do Excel: {row['descricao']}",
                    type=AcquisitionType.INSUMO,  # Default to supplies
                    status=system_status,
                    justification="Importado do arquivo Excel de aquisições",
                    requester_id=user_id,
                    category_id=default_category.id,
                    cost_center_id=default_cost_center.id,
                    quantity=1,
                    unit='un'
                )
                
                db.session.add(acquisition)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Linha {index + 3}: {str(e)}")
                continue
        
        db.session.commit()
        
        return {
            'success': True,
            'imported_count': imported_count,
            'errors': errors
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }

def parse_excel_preview(file_path):
    """Preview Excel file content before import"""
    try:
        df = pd.read_excel(file_path, header=2)
        df.columns = ['numero', 'descricao', 'responsavel_cotacao', 'status']
        df = df.dropna(subset=['numero', 'descricao'])
        
        preview = []
        for index, row in df.head(10).iterrows():
            preview.append({
                'numero': row['numero'],
                'descricao': str(row['descricao'])[:100],
                'status': str(row['status']) if pd.notna(row['status']) else 'Não informado'
            })
        
        return {
            'success': True,
            'total_rows': len(df),
            'preview': preview
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }