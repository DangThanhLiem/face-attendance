from sqlalchemy import extract
import pandas as pd
from datetime import datetime,date
from app.models import Attendance, Salary, User
from app import db
class ReportGenerator:
    def generate_daily_report(self, date):
        """Generate attendance report for a specific date"""
        # Query all attendance records for the date
        attendances = Attendance.query.filter_by(date=date).all()
        
        # Prepare data for DataFrame
        data = []
        for attendance in attendances:
            duration = None
            if attendance.time_in and attendance.time_out:
                duration = (attendance.time_out - attendance.time_in).total_seconds() / 3600  # hours
            
            data.append({
                'Date': attendance.date,
                'Employee Name': attendance.user.name,
                'Employee ID': attendance.user.id,
                'Time In': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
                'Time Out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None,
                'Duration (Hours)': round(duration, 2) if duration else None,
                'Status': attendance.status
            })
        
        return pd.DataFrame(data)

    def generate_monthly_report(self, year, month):
        """Generate attendance report for a specific month"""
        # Get start and end date for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        
        # Query all attendance records for the month
        attendances = Attendance.query.filter(
            Attendance.date >= start_date,
            Attendance.date < end_date
        ).all()
        
        # Prepare data for DataFrame
        data = []
        for attendance in attendances:
            duration = None
            if attendance.time_in and attendance.time_out:
                duration = (attendance.time_out - attendance.time_in).total_seconds() / 3600
            
            data.append({
                'Date': attendance.date,
                'Employee Name': attendance.user.name,
                'Employee ID': attendance.user.id,
                'Time In': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
                'Time Out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None,
                'Duration (Hours)': round(duration, 2) if duration else None,
                'Status': attendance.status
            })
        
        return pd.DataFrame(data)

    def export_to_excel(self, df, filepath):
        """Export DataFrame to Excel file with better formatting"""
        # Create Excel writer
        writer = pd.ExcelWriter(filepath, engine='xlsxwriter')
        
        # Write DataFrame to Excel
        df.to_excel(writer, sheet_name='Attendance Report', index=False)
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Attendance Report']
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#4F81BD',  # Màu xanh đậm hơn
            'font_color': 'white',   # Chữ màu trắng
            'border': 2,             # Viền đậm hơn
            'font_size': 12,         # Font size lớn hơn
            'border_color': '#2F5597' # Màu viền xanh đậm
        })
        
        cell_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,       # Cho phép wrap text
            'border': 1,
            'font_size': 11,         # Font size lớn hơn
            'border_color': '#B4C6E7' # Màu viền nhạt
        })

        # Định dạng cho các cột ngày tháng
        date_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
            'border': 1,
            'font_size': 11,
            'border_color': '#B4C6E7',
            'num_format': 'dd/mm/yyyy'  # Định dạng ngày tháng
        })
        
        # Write headers with format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Write data with formats
        for row_num in range(len(df)):
            for col_num, value in enumerate(df.iloc[row_num]):
                # Kiểm tra nếu là cột ngày tháng
                if isinstance(value, (datetime, date)):
                    worksheet.write(row_num + 1, col_num, value, date_format)
                elif pd.isna(value):
                    worksheet.write(row_num + 1, col_num, '', cell_format)
                else:
                    worksheet.write(row_num + 1, col_num, value, cell_format)
        
        # Set row height
        worksheet.set_default_row(25)  # Tăng chiều cao mặc định
        worksheet.set_row(0, 30)      # Tăng chiều cao header
        
        # Set column widths với độ rộng tối thiểu
        min_width = 15  # Độ rộng tối thiểu cho mỗi cột
        for idx, col in enumerate(df.columns):
            series = df[col]
            max_len = max(
                series.astype(str).map(len).max(),
                len(str(series.name))
            ) + 3  # Thêm padding
            # Đảm bảo độ rộng nằm trong khoảng min_width đến 40
            width = max(min_width, min(max_len, 40))
            worksheet.set_column(idx, idx, width)
        
        # Freeze panes (header row)
        worksheet.freeze_panes(1, 0)
        
        # Thêm màu nền xen kẽ cho các hàng
        for row_num in range(1, len(df) + 1):
            if row_num % 2 == 0:
                for col_num in range(len(df.columns)):
                    cell_format = workbook.add_format({
                        'align': 'center',
                        'valign': 'vcenter',
                        'text_wrap': True,
                        'border': 1,
                        'font_size': 11,
                        'border_color': '#B4C6E7',
                        'bg_color': '#F2F2F2'  # Màu nền nhạt cho hàng chẵn
                    })
                    worksheet.write(row_num, col_num, df.iloc[row_num-1, col_num], cell_format)
        
        # Close the writer and save the file
        writer.close()

    def generate_employee_report(self, employee_id, start_date, end_date):
        """Generate attendance report for a specific employee"""
        # Query attendance records for the employee
        attendances = Attendance.query.filter(
            Attendance.user_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        # Prepare data for DataFrame
        data = []
        total_hours = 0
        present_days = 0
        
        for attendance in attendances:
            duration = None
            if attendance.time_in and attendance.time_out:
                duration = (attendance.time_out - attendance.time_in).total_seconds() / 3600
                total_hours += duration
                present_days += 1
            
            data.append({
                'Date': attendance.date,
                'Time In': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
                'Time Out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None,
                'Duration (Hours)': round(duration, 2) if duration else None,
                'Status': attendance.status
            })
        
        df = pd.DataFrame(data)
        
        # Add summary information
        summary = pd.DataFrame([{
            'Total Days': (end_date - start_date).days + 1,
            'Present Days': present_days,
            'Absent Days': (end_date - start_date).days + 1 - present_days,
            'Total Hours': round(total_hours, 2),
            'Average Hours/Day': round(total_hours / present_days, 2) if present_days > 0 else 0
        }])
        
        return df, summary
# app/utils/reports.py
class SalaryCalculator:
    def calculate_monthly_salary(self, user_id, month, year):
        user = User.query.get(user_id)
        if not user:
            return None
            
        # Lấy tất cả điểm danh trong tháng
        attendances = Attendance.query.filter(
            Attendance.user_id == user_id,
            extract('month', Attendance.date) == month,
            extract('year', Attendance.date) == year
        ).all()
        
        # Tính tổng giờ làm việc
        total_hours = 0
        for att in attendances:
            if att.check_in and att.check_out:
                hours = (att.check_out - att.check_in).total_seconds() / 3600
                total_hours += hours
                    
        # Tính lương
        total_salary = total_hours * user.hourly_rate
        
        # Lưu thông tin lương
        salary = Salary(
            user_id=user_id,
            month=month,
            year=year,
            total_hours=total_hours,
            total_salary=total_salary
        )
        
        db.session.add(salary)
        db.session.commit()
        
        return salary
