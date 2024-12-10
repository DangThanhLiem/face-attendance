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
from calendar import monthrange
import pandas as pd
from io import BytesIO
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

    try:
        employee = User.query.get_or_404(employee_id)
        
        # Xóa tất cả bản ghi chấm công của nhân viên
        Attendance.query.filter_by(user_id=employee_id).delete()
        
        # Xóa tất cả bản ghi lương của nhân viên
        Salary.query.filter_by(user_id=employee_id).delete()
        
        # Xóa nhân viên
        db.session.delete(employee)
        db.session.commit()
        
        flash('Employee and all related records deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting employee: {str(e)}', 'danger')
    
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

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    date = request.args.get('date')
    employee_id = request.args.get('employee_id')
    report_type = request.args.get('type', 'daily')

    try:
        query = Attendance.query

        # Xử lý các điều kiện lọc
        if date and employee_id:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date == date_obj, Attendance.user_id == employee_id)
            employee = User.query.get(employee_id)
            filename = f'attendance_report_{employee.name}_{date_obj}.xlsx'
        elif date:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            query = query.filter(Attendance.date == date_obj)
            filename = f'attendance_report_{date_obj}.xlsx'
        elif employee_id:
            query = query.filter(Attendance.user_id == employee_id)
            employee = User.query.get(employee_id)
            filename = f'attendance_report_{employee.name}_all_dates.xlsx'
        else:
            filename = 'attendance_report_all.xlsx'

        attendances = query.order_by(Attendance.date.desc(), Attendance.time_in.asc()).all()

        data = []
        total_hours = 0
        for att in attendances:
            user = User.query.get(att.user_id)
            working_hours = 0
            if att.time_in and att.time_out:
                time_diff = att.time_out - att.time_in
                working_hours = round(time_diff.total_seconds()/3600, 2)
                total_hours += working_hours
            
            data.append({
                'Date': att.date.strftime('%Y-%m-%d'),
                'Employee Name': user.name,
                'Position': user.position,
                'Check In': att.time_in.strftime('%H:%M:%S') if att.time_in else 'N/A',
                'Check Out': att.time_out.strftime('%H:%M:%S') if att.time_out else 'N/A',
                'Working Hours': working_hours
            })

        df = pd.DataFrame(data)
        filepath = os.path.join(reports_dir, filename)

        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            if len(data) > 0:
                # Tạo worksheet và viết dữ liệu
                df.to_excel(writer, sheet_name='Attendance Data', index=False, startrow=1, startcol=0)
                worksheet = writer.sheets['Attendance Data']
                workbook = writer.book

                # Định dạng cho tiêu đề
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 16,
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_color': '#0066cc'
                })

                # Định dạng cho header
                header_format = workbook.add_format({
                    'bold': True,
                    'font_size': 11,
                    'bg_color': '#4F81BD',
                    'font_color': 'white',
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#2E75B6'
                })

                # Định dạng cho dữ liệu
                data_format = workbook.add_format({
                    'font_size': 10,
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#BDD7EE'
                })

                # Định dạng cho dòng tổng
                total_format = workbook.add_format({
                    'bold': True,
                    'font_size': 11,
                    'bg_color': '#FFE699',
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 2,
                    'border_color': '#ED7D31',
                    'num_format': '#,##0.00'
                })

                # Định dạng cho số giờ
                hours_format = workbook.add_format({
                    'font_size': 10,
                    'align': 'center',
                    'valign': 'vcenter',
                    'border': 1,
                    'border_color': '#BDD7EE',
                    'num_format': '#,##0.00'
                })

                # Viết tiêu đề báo cáo
                title = 'ATTENDANCE REPORT'
                if date:
                    title += f' - {date}'
                if employee_id:
                    employee = User.query.get(employee_id)
                    title += f' - {employee.name}'
                
                worksheet.merge_range('A1:F1', title, title_format)

                # Áp dụng định dạng cho header
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(1, col_num, value, header_format)

                # Áp dụng định dạng cho dữ liệu
                for row_num in range(len(df)):
                    for col_num in range(len(df.columns)):
                        value = df.iloc[row_num, col_num]
                        if col_num == 5:  # Working Hours column
                            worksheet.write(row_num + 2, col_num, value, hours_format)
                        else:
                            worksheet.write(row_num + 2, col_num, value, data_format)

                # Thêm dòng tổng kết
                total_row = len(df) + 2
                worksheet.merge_range(f'A{total_row+1}:E{total_row+1}', 'Total', total_format)
                worksheet.write(total_row, 5, total_hours, total_format)

                # Tự động điều chỉnh độ rộng cột
                worksheet.set_column('A:A', 12)  # Date
                worksheet.set_column('B:B', 20)  # Employee Name
                worksheet.set_column('C:C', 15)  # Position
                worksheet.set_column('D:E', 12)  # Check In/Out
                worksheet.set_column('F:F', 15)  # Working Hours

                # Thêm đường viền cho toàn bộ bảng
                worksheet.conditional_format(1, 0, total_row, 5, {
                    'type': 'no_blanks',
                    'format': data_format
                })

            else:
                worksheet = writer.book.add_worksheet('No Data')
                no_data_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_color': 'red'
                })
                worksheet.merge_range('A1:F1', 'No attendance records found for the selected criteria', no_data_format)

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error in export_report: {str(e)}")
        flash(f'Error generating report: {str(e)}', 'danger')
        return redirect(url_for('admin.reports'))






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
    
    salary_records = Salary.query.filter_by(month=month, year=year).all()
    
    salary_data = []
    total_salary = 0
    total_hours = 0
    
    for record in salary_records:
        employee = User.query.get(record.user_id)
        if employee:
            total_salary += record.total_salary
            total_hours += record.total_hours
            salary_data.append({
                'Employee Name': employee.name,
                'Position': employee.position or 'N/A',
                'Hourly Rate': employee.hourly_rate or 0,
                'Total Hours': round(record.total_hours, 2),
                'Total Salary': round(record.total_salary, 2)
            })
    
    df = pd.DataFrame(salary_data)
    filename = f'salary_report_{month}_{year}.xlsx'
    reports_dir = 'D:/face-recognition/reports'
    
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    filepath = os.path.join(reports_dir, filename)
    
    with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
        if len(salary_data) > 0:
            df.to_excel(writer, sheet_name='Salary Report', index=False, startrow=1, startcol=0)
            worksheet = writer.sheets['Salary Report']
            workbook = writer.book

            # Định dạng cho tiêu đề
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'font_color': '#0066cc'
            })

            # Định dạng cho header
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'bg_color': '#4F81BD',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#2E75B6'
            })

            # Định dạng cho dữ liệu
            data_format = workbook.add_format({
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#BDD7EE'
            })

            # Định dạng cho số tiền
            money_format = workbook.add_format({
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#BDD7EE',
                'num_format': '$#,##0'
            })

            # Định dạng cho số giờ
            hours_format = workbook.add_format({
                'font_size': 10,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#BDD7EE',
                'num_format': '#,##0.00'
            })

            # Định dạng cho dòng tổng
            total_format = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'bg_color': '#FFE699',
                'align': 'center',
                'valign': 'vcenter',
                'border': 2,
                'border_color': '#ED7D31'
            })

            # Định dạng cho dòng tổng với số tiền
            total_format_money = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'bg_color': '#FFE699',
                'align': 'center',
                'valign': 'vcenter',
                'border': 2,
                'border_color': '#ED7D31',
                'num_format': '$#,##0'
            })

            # Định dạng cho dòng tổng với số giờ
            total_format_hours = workbook.add_format({
                'bold': True,
                'font_size': 11,
                'bg_color': '#FFE699',
                'align': 'center',
                'valign': 'vcenter',
                'border': 2,
                'border_color': '#ED7D31',
                'num_format': '#,##0.00'
            })

            # Viết tiêu đề báo cáo
            title = f'SALARY REPORT - {month}/{year}'
            worksheet.merge_range('A1:E1', title, title_format)

            # Áp dụng định dạng cho header
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(1, col_num, value, header_format)

            # Áp dụng định dạng cho dữ liệu
            for row_num in range(len(df)):
                for col_num in range(len(df.columns)):
                    value = df.iloc[row_num, col_num]
                    if col_num in [2, 4]:  # Hourly Rate và Total Salary
                        worksheet.write(row_num + 2, col_num, value, money_format)
                    elif col_num == 3:  # Total Hours
                        worksheet.write(row_num + 2, col_num, value, hours_format)
                    else:
                        worksheet.write(row_num + 2, col_num, value, data_format)

            # Thêm dòng tổng kết
            total_row = len(df) + 2
            worksheet.merge_range(f'A{total_row+1}:C{total_row+1}', 'Total', total_format)
            worksheet.write(total_row, 3, total_hours, total_format_hours)
            worksheet.write(total_row, 4, total_salary, total_format_money)

            # Tự động điều chỉnh độ rộng cột
            worksheet.set_column('A:A', 20)  # Employee Name
            worksheet.set_column('B:B', 15)  # Position
            worksheet.set_column('C:C', 12)  # Hourly Rate
            worksheet.set_column('D:D', 12)  # Total Hours
            worksheet.set_column('E:E', 15)  # Total Salary

            # Thêm đường viền cho toàn bộ bảng
            worksheet.conditional_format(1, 0, total_row, 4, {
                'type': 'no_blanks',
                'format': data_format
            })

            # Thêm thông tin thống kê
            stats_row = total_row + 3
            stats_format = workbook.add_format({
                'font_size': 11,
                'align': 'left',
                'valign': 'vcenter'
            })
            worksheet.write(stats_row, 0, f'Report Period: {month}/{year}', stats_format)
            worksheet.write(stats_row + 1, 0, f'Total Employees: {len(salary_data)}', stats_format)
            worksheet.write(stats_row + 2, 0, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M")}', stats_format)

        else:
            worksheet = writer.book.add_worksheet('No Data')
            no_data_format = workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'valign': 'vcenter',
                'font_color': 'red'
            })
            worksheet.merge_range('A1:E1', 'No salary records found for the selected period', no_data_format)

    return send_file(
        filepath,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
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