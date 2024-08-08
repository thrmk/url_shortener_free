from flask import Blueprint, render_template, request,flash
from ..utils import convert_units

unit_converter_bp = Blueprint('unit_converter', __name__)

@unit_converter_bp.route('/unit_converter', methods=['GET', 'POST'])
def unit_converter():
    value = ''
    from_unit = ''
    to_unit = ''
    category = ''
    result = None

    units = {
        'distance': ['meters', 'kilometers', 'miles', 'yards', 'feet', 'inches', 'centimeters', 'millimeters', 'nautical miles'],
        'weight': ['grams', 'kilograms', 'pounds', 'ounces', 'milligrams', 'micrograms', 'stones', 'tons', 'carats'],
        'temperature': ['celsius', 'fahrenheit', 'kelvin', 'rankine'],
        'volume': ['liters', 'milliliters', 'gallons', 'cups', 'pints', 'quarts', 'cubic meters', 'cubic centimeters', 'cubic inches'],
        'data': ['bytes', 'kilobytes', 'megabytes', 'gigabytes', 'terabytes', 'petabytes', 'exabytes', 'zettabytes', 'yottabytes'],
        # Add more categories and units as needed
    }

    if request.method == 'POST':
        try:
            value = float(request.form['value'])
            category = request.form['category']
            from_unit = request.form['from_unit']
            to_unit = request.form['to_unit']

            result = convert_units(value, from_unit, to_unit, category)
        except ValueError:
            flash('Please enter a valid number.')

    return render_template('unit_converter.html', result=result, value=value, from_unit=from_unit, to_unit=to_unit, category=category, units=units)