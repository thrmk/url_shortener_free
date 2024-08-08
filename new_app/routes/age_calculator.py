from flask import Blueprint, render_template, request
from datetime import datetime
from dateutil.relativedelta import relativedelta

age_calculator_bp = Blueprint('age_calculator', __name__)

@age_calculator_bp.route('/age_calculator', methods=['GET', 'POST'])
def age_calculator():
    age_details = None
    total_days = None
    format_type = request.form.get('format_type', 'full')

    if request.method == 'POST':
        try:
            dob_str = request.form.get('dob')
            dob = datetime.strptime(dob_str, '%Y-%m-%d')
            today = datetime.today()

            age = relativedelta(today, dob)
            age_details = {
                'years': age.years,
                'months': age.months,
                'days': age.days,
                'total_days': (today - dob).days,
                'time': today - dob
            }

            if format_type == 'days':
                age_details = {
                    'days': age_details['total_days']
                }
            elif format_type == 'months':
                age_details = {
                    'months': age.years * 12 + age.months
                }
            elif format_type == 'time':
                age_details = {
                    'time': age_details['time']
                }
            elif format_type == 'full':
                pass  # Use the full detailed age

        except ValueError:
            age_details = 'Invalid date format. Please enter a valid date.'

    return render_template('age_calculator.html', age_details=age_details, format_type=format_type)
