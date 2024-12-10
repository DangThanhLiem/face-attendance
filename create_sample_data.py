from app import db, create_app
from app.models import User, Attendance, Salary
from datetime import datetime, timedelta
import random

def create_sample_data():
    app = create_app()
    with app.app_context():
        # Xóa dữ liệu cũ
        Salary.query.delete()
        Attendance.query.delete()
        User.query.delete()
        db.session.commit()

        # Tạo danh sách positions
        positions = ['Manager', 'Developer', 'Designer', 'HR', 'Accountant', 'Sales', 'Marketing']
        
        # Tạo 20 nhân viên mẫu
        employees = []
        for i in range(1, 21):
            employee = User(
                name=f'Employee {i}',
                username=f'emp{i}',
                email=f'employee{i}@example.com',
                position=random.choice(positions),
                hourly_rate=round(random.uniform(15.0, 50.0), 2),  # Random hourly rate between $15-$50
                is_admin=False
            )
            employee.set_password('password')
            employees.append(employee)
            db.session.add(employee)
        
        # Tạo tài khoản admin
        admin = User(
            name='Admin',
            username='admin',
            email='admin@example.com',
            position='Administrator',
            is_admin=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        
        db.session.commit()

        # Tạo dữ liệu chấm công cho 30 ngày gần nhất
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        current_date = start_date

        while current_date <= end_date:
            for employee in employees:
                # 80% chance of attendance
                if random.random() < 0.8:
                    # Random time between 7:00 AM and 9:30 AM
                    time_in = current_date.replace(
                        hour=random.randint(7, 9),
                        minute=random.randint(0, 30),
                        second=random.randint(0, 59)
                    )

                    # Tạo attendance record
                    attendance = Attendance(
                        user_id=employee.id,
                        date=current_date.date(),
                        time_in=time_in
                    )

                    # Set time_out (4-6 PM)
                    time_out = current_date.replace(
                        hour=random.randint(16, 18),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    attendance.time_out = time_out
                    
                    db.session.add(attendance)
            
            current_date += timedelta(days=1)
        
        db.session.commit()

        # Tạo dữ liệu lương cho 3 tháng gần nhất
        current_month = datetime.now().month
        current_year = datetime.now().year

        for i in range(3):
            month = current_month - i
            year = current_year
            if month <= 0:
                month += 12
                year -= 1

            for employee in employees:
                # Tính tổng giờ làm việc trong tháng
                attendances = Attendance.query.filter(
                    Attendance.user_id == employee.id,
                    db.extract('month', Attendance.date) == month,
                    db.extract('year', Attendance.date) == year
                ).all()

                total_hours = 0
                for att in attendances:
                    if att.time_out:
                        duration = att.time_out - att.time_in
                        total_hours += duration.total_seconds() / 3600  # Convert to hours

                total_salary = total_hours * employee.hourly_rate

                salary = Salary(
                    user_id=employee.id,
                    month=month,
                    year=year,
                    total_hours=round(total_hours, 2),
                    total_salary=round(total_salary, 2)
                )
                db.session.add(salary)

        db.session.commit()
        print("Sample data created successfully!")

if __name__ == '__main__':
    create_sample_data()
