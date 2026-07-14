from flask import Blueprint, render_template, request, jsonify
from .email_utils import send_feedback_email

feedback_bp = Blueprint(
    'feedback',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/feedback/static'
)

@feedback_bp.route('/modal')
def feedback_modal():
    return render_template('feedback.html')

@feedback_bp.route('/send', methods=['POST'])
def send_feedback():
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        image_data = request.form.get('image_data', '').strip()
        image_filename = request.form.get('image_filename', '').strip()

        if not name or not description:
            return jsonify({'success': False, 'message': 'Name and description are required.'})

        sent = send_feedback_email(name, description, image_data if image_data else None, image_filename if image_filename else None)

        if sent:
            return jsonify({'success': True, 'message': 'Feedback sent.'})
        else:
            return jsonify({'success': False, 'message': 'Could not send feedback. Try again.'})

    except Exception as e:
        print('FEEDBACK ROUTE ERROR:', e)
        return jsonify({'success': False, 'message': 'Something went wrong.'})