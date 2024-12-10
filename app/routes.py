import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import extract
from werkzeug.security import generate_password_hash
from app.models import Salary, User, Attendance
from app.utils.face_utils import FaceRecognitionSystem
from app.utils.reports import ReportGenerator
from app import db
from datetime import datetime
import os

# Tạo các blueprint
auth = Blueprint('auth', __name__)
admin = Blueprint('admin', __name__, url_prefix='/admin')
employee = Blueprint('employee', __name__, url_prefix='/employee')

# Auth routes
@auth.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('employee.dashboard'))
    return redirect(url_for('auth.login'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('employee.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard' if user.is_admin else 'employee.dashboard'))
        
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Admin routes
@admin.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))
    
    employees = User.query.filter_by(is_admin=False).all()
    today = datetime.now().date()
    attendance_count = Attendance.query.filter_by(date=today).count()
    
    return render_template('admin/dashboard.html', 
                         employees=employees,
                         attendance_count=attendance_count,
                         today=today)


@admin.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        position = request.form.get('position')
        hourly_rate = float(request.form.get('hourly_rate', 0))
        
        # Validate input
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('admin/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return render_template('admin/register.html')

        # Create new user
        user = User(
            username=username,
            email=email,
            name=name,
            position=position,
            hourly_rate=hourly_rate,
            is_admin=False
        )
        user.set_password(password)

        # Process face image
        face_image = request.files.get('face_image')
        if face_image:
            try:
                face_recognition = FaceRecognitionSystem()
                success, message = face_recognition.save_face_image(face_image.read(), user)
                if not success:
                    flash(message, 'danger')
                    return render_template('admin/register.html')
            except Exception as e:
                flash(f'Error processing face image: {str(e)}', 'danger')
                return render_template('admin/register.html')
        else:
            flash('Face image is required', 'danger')
            return render_template('admin/register.html')

        try:
            db.session.add(user)
            db.session.commit()
            flash('Employee registered successfully', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering employee: {str(e)}', 'danger')
            return render_template('admin/register.html')

    return render_template('admin/register.html')
# Route sửa nhân viên
@admin.route('/edit-employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))

    employee = User.query.get_or_404(employee_id)

    if request.method == 'POST':
        employee.username = request.form.get('username')
        employee.email = request.form.get('email')
        employee.name = request.form.get('name')
        employee.position = request.form.get('position')
        employee.hourly_rate = float(request.form.get('hourly_rate', 0))
        # Cập nhật mật khẩu nếu có
        password = request.form.get('password')
        if password:
            employee.set_password(password)

        # Xử lý ảnh mới từ webcam
        face_image_data = request.form.get('face_image')
        if face_image_data:
            try:
                # Xử lý và lưu ảnh từ dữ liệu base64
                face_image_data = face_image_data.split(',')[1]  # Lấy phần dữ liệu base64
                face_image = base64.b64decode(face_image_data)  # Giải mã base64
                face_recognition = FaceRecognitionSystem()
                success, message = face_recognition.save_face_image(face_image, employee)
                if not success:
                    flash(message, 'danger')
                    return render_template('admin/edit_employee.html', employee=employee)
            except Exception as e:
                flash(f'Error processing face image: {str(e)}', 'danger')
                return render_template('admin/edit_employee.html', employee=employee)

        db.session.commit()
        flash('Employee updated successfully', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/edit_employee.html', employee=employee)
# Route xóa nhân viên
@admin.route('/delete-employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))

    employee = User.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully', 'success')
    return redirect(url_for('admin.dashboard'))

@admin.route('/reports')
@login_required
def reports():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))

    date = request.args.get('date', datetime.now().date())
    employee_id = request.args.get('employee_id')
    
    query = Attendance.query
    if date:
        query = query.filter_by(date=date)
    if employee_id:
        query = query.filter_by(user_id=employee_id)
    
    attendances = query.all()
    employees = User.query.filter_by(is_admin=False).all()
    
    return render_template('admin/reports.html',
                         attendances=attendances,
                         employees=employees,
                         selected_date=date,
                         selected_employee=employee_id)

@admin.route('/export-report')
@login_required
def export_report():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))

    # Tạo thư mục reports nếu chưa tồn tại
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    date = request.args.get('date')
    employee_id = request.args.get('employee_id')
    report_type = request.args.get('type', 'daily')

    report_generator = ReportGenerator()

    try:
        if report_type == 'daily':
            if date:
                date = datetime.strptime(date, '%Y-%m-%d').date()
                df = report_generator.generate_daily_report(date)
                filename = f'daily_attendance_report_{date}.xlsx'
            else:
                today = datetime.now().date()
                df = report_generator.generate_daily_report(today)
                filename = f'daily_attendance_report_{today}.xlsx'
        
        elif report_type == 'monthly':
            today = datetime.now()
            df = report_generator.generate_monthly_report(today.year, today.month)
            filename = f'monthly_attendance_report_{today.year}_{today.month}.xlsx'
        
        elif report_type == 'employee' and employee_id:
            start_date = datetime.strptime(request.args.get('start_date', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.args.get('end_date', ''), '%Y-%m-%d').date()
            df, summary = report_generator.generate_employee_report(employee_id, start_date, end_date)
            filename = f'employee_attendance_report_{employee_id}.xlsx'
        else:
            flash('Invalid report type or missing parameters', 'danger')
            return redirect(url_for('admin.reports'))

        # Tạo đường dẫn đầy đủ cho file
        filepath = os.path.join(reports_dir, filename)
        
        # Xuất file Excel
        report_generator.export_to_excel(df, filepath)
        
        # Gửi file về client
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('admin.reports'))
from sqlalchemy import extract
from datetime import datetime
from calendar import monthrange

@admin.route('/salary-report')
@login_required
def salary_report():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    _, last_day = monthrange(year, month)
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, last_day)
    
    employees = User.query.filter_by(is_admin=False).all()
    
    # Kiểm tra xem đã có báo cáo lương cho tháng này chưa
    salary_data = []
    for employee in employees:
        # Tìm báo cáo lương đã tồn tại
        existing_salary = Salary.query.filter_by(
            user_id=employee.id,
            month=month,
            year=year
        ).first()
        
        if existing_salary:
            # Nếu đã có báo cáo, sử dụng dữ liệu có sẵn
            salary_info = {
                'employee': employee,
                'total_hours': existing_salary.total_hours,
                'hourly_rate': employee.hourly_rate or 0,
                'total_salary': existing_salary.total_salary,
                'attendance_days': Attendance.query.filter(
                    Attendance.user_id == employee.id,
                    Attendance.date >= start_date.date(),
                    Attendance.date <= end_date.date()
                ).count()
            }
        else:
            # Nếu chưa có, tính toán mới
            attendances = Attendance.query.filter(
                Attendance.user_id == employee.id,
                Attendance.date >= start_date.date(),
                Attendance.date <= end_date.date()
            ).all()
            
            total_hours = 0
            for att in attendances:
                if att.time_in and att.time_out:
                    time_diff = att.time_out - att.time_in
                    hours = time_diff.total_seconds() / 3600
                    total_hours += hours
            
            total_salary = total_hours * (employee.hourly_rate or 0)
            
            # Tạo bản ghi lương mới
            new_salary = Salary(
                user_id=employee.id,
                month=month,
                year=year,
                total_hours=total_hours,
                total_salary=total_salary
            )
            
            try:
                db.session.add(new_salary)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving salary data: {str(e)}', 'danger')
            
            salary_info = {
                'employee': employee,
                'total_hours': total_hours,
                'hourly_rate': employee.hourly_rate or 0,
                'total_salary': total_salary,
                'attendance_days': len(attendances)
            }
        
        salary_data.append(salary_info)
    
    return render_template('admin/salary_report.html',
                         salary_data=salary_data,
                         current_month=month,
                         current_year=year)

@admin.route('/export-salary-report')
@login_required
def export_salary_report():
    if not current_user.is_admin:
        return redirect(url_for('employee.dashboard'))
    
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Lấy tất cả bản ghi lương của tháng/năm được chọn
    salary_records = Salary.query.filter_by(month=month, year=year).all()
    
    salary_data = []
    for record in salary_records:
        employee = User.query.get(record.user_id)
        if employee:
            salary_data.append({
                'Employee Name': employee.name,
                'Position': employee.position or 'N/A',
                'Hourly Rate': employee.hourly_rate or 0,
                'Total Hours': round(record.total_hours, 2),
                'Total Salary': round(record.total_salary, 2),
                'Month': f"{month}/{year}",
                'Generated Date': record.created_at.strftime('%Y-%m-%d %H:%M')
            })
    
    # Tạo Excel file
    import pandas as pd
    from io import BytesIO
    
    df = pd.DataFrame(salary_data)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Salary Report', index=False)
        
        # Tự động điều chỉnh độ rộng cột
        worksheet = writer.sheets['Salary Report']
        for idx, col in enumerate(df.columns):
            series = df[col]
            max_len = max(
                series.astype(str).map(len).max(),
                len(str(series.name))
            ) + 1
            worksheet.set_column(idx, idx, max_len)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'salary_report_{month}_{year}.xlsx'
    )


# Employee routes
@employee.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    today = datetime.now().date()
    attendance = Attendance.query.filter_by(
        user_id=current_user.id,
        date=today
    ).first()

    return render_template('employee/dashboard.html',
                         attendance=attendance)

@employee.route('/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    if current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admins cannot mark attendance'})

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image provided'})

    image_file = request.files['image']
    face_recognition = FaceRecognitionSystem()
    
    try:
        success, message = face_recognition.process_attendance(image_file.read(), current_user)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'status': 'Present',
                'time': datetime.now().strftime('%H:%M:%S')
            })
        return jsonify({'success': False, 'message': message})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@employee.route('/attendance')
@login_required
def attendance():
    if current_user.is_admin:
        return redirect(url_for('admin.dashboard'))

    attendances = Attendance.query.filter_by(user_id=current_user.id).order_by(Attendance.date.desc()).all()
    return render_template('employee/attendance.html',
                         attendances=attendances)