from flask import Blueprint, render_template, request,flash
from ..utils import generate_password, assess_password_strength

password_generator_bp = Blueprint('password_generator', __name__)

@password_generator_bp.route('/password_generator', methods=['GET', 'POST'])
def password_generator():
    password = None
    strength = None
    color = "red"

    # Default settings
    include_uppercase = False
    include_digits = False
    include_special = False
    length = 12

    if request.method == 'POST':
        length = int(request.form.get('length', 12))
        include_uppercase = 'uppercase' in request.form
        include_digits = 'digits' in request.form
        include_special = 'special' in request.form

        password = generate_password(length, include_uppercase, include_digits, include_special)
        strength, color = assess_password_strength(password)

    return render_template(
        'password_generator.html',
        password=password,
        strength=strength,
        color=color,
        length=length,
        include_uppercase=include_uppercase,
        include_digits=include_digits,
        include_special=include_special
    )
