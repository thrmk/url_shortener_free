from flask import Blueprint, render_template, request, flash
from ..utils import calculate_bmi

bmi_bp = Blueprint('bmi', __name__)

@bmi_bp.route('/bmi', methods=['GET', 'POST'])
def bmi():
    bmi = None
    category = ''
    
    if request.method == 'POST':
        try:
            weight = float(request.form.get('weight', 0))
            weight_unit = request.form.get('weight_unit', 'kg')
            height = float(request.form.get('height', 0))
            height_unit = request.form.get('height_unit', 'cm')
            
            bmi = calculate_bmi(weight, weight_unit, height, height_unit)

            if bmi is not None:
                if bmi < 18.5:
                    category = 'Underweight'
                elif 18.5 <= bmi < 24.9:
                    category = 'Normal weight'
                elif 25 <= bmi < 29.9:
                    category = 'Overweight'
                else:
                    category = 'Obesity'
            else:
                flash('Invalid input. Please enter valid numbers for weight and height.')
        except ValueError:
            flash('Please enter valid numeric values for weight and height.')

    return render_template('bmi.html', bmi=bmi, category=category)