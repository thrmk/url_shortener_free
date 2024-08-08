from flask import Blueprint, url_for, flash, redirect
from ..database import get_db_connection

delete_url_bp = Blueprint('delete_url', __name__)

@delete_url_bp.route('/delete_url/<int:id>', methods=['POST'])
def delete_url(id):
    # Directly use the integer ID without decoding since it's coming as an integer
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM urls WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        flash('Failed to delete URL. It may not exist.')
    else:
        flash('URL deleted successfully.')

    return redirect(url_for('stats'))